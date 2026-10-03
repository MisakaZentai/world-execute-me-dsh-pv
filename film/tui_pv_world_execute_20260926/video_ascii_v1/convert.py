"""CPU video -> stable, contour-aware monospace glyph video. Pillow + ffmpeg only."""
from __future__ import annotations
import argparse,collections,hashlib,html,json,math,os,statistics,subprocess,time
from urllib.parse import quote
from fractions import Fraction
from functools import lru_cache
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

HERE=Path(__file__).resolve().parent
BG=(7,16,29)
PRESETS={'readable':(6,12,11),'dense':(6,10,10)}
FONT_PATH=r'C:\Windows\Fonts\consola.ttf'
RAMP=' .,:;irsXA253hMHGS#9B&@'
MILI=Path(__file__).resolve().parents[3].joinpath("input", "song.mp3")
MILI_START=58.7740846

def run_json(command):
    p=subprocess.run(command,capture_output=True,text=True,check=True);return json.loads(p.stdout)
def probe(path,frames=False):
    cmd=['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(path)]
    data=run_json(cmd);video=next(s for s in data['streams'] if s['codec_type']=='video')
    if frames:
        detail=run_json(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time,pkt_duration_time','-of','json',str(path)])
        pts=[float(x['best_effort_timestamp_time']) for x in detail['frames'] if 'best_effort_timestamp_time' in x]
        data['video_frame_pts']=pts
    return data,video
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def corner_color(im):
    w,h=im.size;points=[]
    for xx in (.015,.045,.955,.985):
        for yy in (.015,.045,.955,.985):points.append(im.getpixel((min(w-1,int(w*xx)),min(h-1,int(h*yy)))))
    return tuple(int(statistics.median(v[c] for v in points)) for c in range(3))
def display_geometry(stream,width,height):
    try:sar=float(Fraction(stream.get('sample_aspect_ratio','1:1').replace(':','/')))
    except (ValueError,ZeroDivisionError):sar=1.0
    rotation=next((float(s.get('rotation',0)) for s in stream.get('side_data_list',[]) if 'rotation' in s),float(stream.get('tags',{}).get('rotate',0)))
    sw,sh=int(stream['width'])*sar,int(stream['height'])
    if round(rotation)%180:sw,sh=sh,sw
    ratio=min(width/sw,height/sh)
    return max(2,round(sw*ratio)),max(2,round(sh*ratio)),sw/sh,rotation,sar

class Converter:
    def __init__(self,width=1920,height=1080,preset='readable',background='auto',tolerance=20,hysteresis=3,bright=False,white_pockets=0):
        self.width,self.height=width,height;self.cw,self.ch,self.font_size=PRESETS[preset]
        self.cols,self.rows=width//self.cw,height//self.ch
        self.background=background;self.tolerance=tolerance;self.hysteresis=hysteresis
        self.previous=None;self.anchor=None;self.previous_colors=None;self.previous_edges=None
        self.bright=bright;self.white_pockets=white_pockets
        self.font=ImageFont.truetype(r'C:\Windows\Fonts\consolab.ttf' if bright else FONT_PATH,self.font_size)
        self.stats={'frames':0,'held_glyphs':0,'held_edge_glyphs':0,'visibility_changes_immediate':0}
    def fit(self,im):
        factor=min(self.width/im.width,self.height/im.height)
        size=(max(1,round(im.width*factor)),max(1,round(im.height*factor)))
        resized=im.resize(size,Image.Resampling.LANCZOS) if size!=im.size else im
        return resized,((self.width-size[0])//2,(self.height-size[1])//2)
    def cells(self,im):
        fitted,(ox,oy)=self.fit(im)
        background=corner_color(fitted) if self.background=='auto' else (0,0,0) if self.background=='dark' else (255,255,255) if self.background=='light' else BG
        # Analysis padding uses source background; output padding is always dark/blank.
        canvas=Image.new('RGB',(self.width,self.height),background);canvas.paste(fitted,(ox,oy))
        tiny=canvas.resize((self.cols,self.rows),Image.Resampling.BOX)
        colors=list(tiny.getdata());lum=[(54*r+183*g+19*b)//256 for r,g,b in colors]
        n=len(colors);pad=[False]*n
        for y in range(self.rows):
            for x in range(self.cols):
                px=(x+.5)*self.cw;py=(y+.5)*self.ch
                pad[y*self.cols+x]=not(ox<=px<ox+fitted.width and oy<=py<oy+fitted.height)
        mask=pad[:]
        if self.background!='none':
            candidate=[max(abs(v[c]-background[c]) for c in range(3))<=self.tolerance or pad[i] for i,v in enumerate(colors)]
            # Only border-connected background is removed. Interior dark cloth survives.
            queue=collections.deque()
            for y in range(self.rows):
                for x in (0,self.cols-1):
                    i=y*self.cols+x
                    if candidate[i] and not mask[i]:mask[i]=True;queue.append(i)
                    elif pad[i]:queue.append(i)
            for x in range(self.cols):
                for y in (0,self.rows-1):
                    i=y*self.cols+x
                    if candidate[i] and not mask[i]:mask[i]=True;queue.append(i)
                    elif pad[i]:queue.append(i)
            visited=set(queue)
            while queue:
                i=queue.popleft();x=i%self.cols;y=i//self.cols
                for j in ((i-1 if x else -1),(i+1 if x<self.cols-1 else -1),(i-self.cols if y else -1),(i+self.cols if y<self.rows-1 else -1)):
                    if j>=0 and j not in visited and candidate[j]:mask[j]=True;visited.add(j);queue.append(j)
        # Optional near-neutral white removal also reaches enclosed background pockets.
        # Kept separate from broad flood tolerance to protect off-white shaded fabric.
        pocket_count=0
        if self.white_pockets and min(background)>=240 and self.background!='none':
            for i,rgb in enumerate(colors):
                if not mask[i] and min(rgb)>=self.white_pockets and max(rgb)-min(rgb)<=5:
                    mask[i]=True;pocket_count+=1
        chars=[];edges=[];anchors=[];held=0;visible_changed=0
        for i,((r,g,b),light) in enumerate(zip(colors,lum)):
            if mask[i]:chars.append(' ');edges.append(0);anchors.append(light);continue
            x=i%self.cols;y=i//self.cols
            left=i-1 if x else i;right=i+1 if x<self.cols-1 else i;up=i-self.cols if y else i;down=i+self.cols if y<self.rows-1 else i
            dx=lum[right]-lum[left];dy=lum[down]-lum[up]
            boundary=any(mask[j] for j in (left,right,up,down))
            strong=abs(dx)+abs(dy)>76
            edge=(1 if abs(dx)>abs(dy)*1.7 else 2 if abs(dy)>abs(dx)*1.7 else 3 if dx*dy>0 else 4) if strong or boundary else 0
            density=round((.45+.55*light/255)*(len(RAMP)-1)) if self.bright else round(light/255*(len(RAMP)-1))
            glyph=('|' if edge==1 else '_' if edge==2 else '/' if edge==3 else '\\') if edge else RAMP[max(1,min(len(RAMP)-1,density))]
            anchor=light
            if self.previous is not None:
                old=self.previous[i]
                if (old==' ')!=(glyph==' '):visible_changed+=1
                # No averaging, spatial history or trails. Moving/strong edges never hold.
                if not edge and not self.previous_edges[i] and old!=' ' and glyph!=old and abs(light-self.anchor[i])<=self.hysteresis and max(abs(colors[i][j]-self.previous_colors[i][j]) for j in range(3))<=8:
                    glyph=old;anchor=self.anchor[i];held+=1
            chars.append(glyph);edges.append(edge);anchors.append(anchor)
        self.previous=chars[:];self.previous_colors=colors;self.previous_edges=edges;self.anchor=anchors
        self.stats['frames']+=1;self.stats['held_glyphs']+=held;self.stats['visibility_changes_immediate']+=visible_changed
        outcolors=[tuple(min(248,max(136,round((v*.52+116)/8)*8)) if self.bright else min(248,max(82,round((v*.83+39)/16)*16)) for v in rgb) for rgb in colors]
        return chars,outcolors,{'masked_cells':sum(mask),'white_pocket_cells':pocket_count,'edge_cells':sum(bool(x) for x in edges),'held_cells':held,'background_estimate':background,'source_fit_pixels':[ox,oy,fitted.width,fitted.height]}
    @lru_cache(maxsize=24000)
    def tile(self,glyph,color):
        tile=Image.new('RGB',(self.cw,self.ch),BG);d=ImageDraw.Draw(tile);d.text((0,-1),glyph,font=self.font,fill=color);return tile
    def render(self,chars,colors,mono=False):
        im=Image.new('RGB',(self.width,self.height),BG)
        for i,glyph in enumerate(chars):
            if glyph!=' ':im.paste(self.tile(glyph,(216,231,242) if mono else colors[i]),((i%self.cols)*self.cw,(i//self.cols)*self.ch))
        return im
    def text(self,chars):return '\n'.join(''.join(chars[y*self.cols:(y+1)*self.cols]).rstrip() for y in range(self.rows))+'\n'

def export(args):
    source=Path(args.input).resolve();out=Path(args.output).resolve()
    if args.width<64 or args.height<64 or args.width%2 or args.height%2:raise ValueError('H264 output dimensions must be even and at least 64 pixels.')
    if HERE not in out.parents:raise ValueError('Output must be a new child directory inside video_ascii_v1.')
    if out.exists() and any(out.iterdir()):raise ValueError('Output directory is nonempty; choose a fresh run directory to preserve prior output.')
    out.mkdir(parents=True,exist_ok=True)
    before,vs=probe(source,True);pts=before['video_frame_pts'];fps=Fraction(args.fps or vs.get('avg_frame_rate') or vs['r_frame_rate'])
    if fps<=0:raise ValueError('Invalid frame rate; supply --fps.')
    duration=float(vs.get('duration') or before['format']['duration'])
    if duration>args.max_seconds:raise ValueError(f'{duration:.3f}s exceeds bounded --max-seconds {args.max_seconds}; no truncation performed.')
    intervals=[b-a for a,b in zip(pts,pts[1:])];vfr=bool(intervals and max(abs(x-1/float(fps)) for x in intervals)>.002)
    converter=Converter(args.width,args.height,args.preset,args.background,args.mask_tolerance,args.hysteresis,args.bright,args.white_pockets)
    # Decode at full fitted source detail. No crop; fps normalization changes no duration/speed.
    dw,dh,display_aspect,rotation,sar=display_geometry(vs,args.width,args.height)
    decoder_cmd=['ffmpeg','-hide_banner','-v','error','-i',str(source),'-an','-vf',f'fps={fps.numerator}/{fps.denominator},scale={dw}:{dh}:flags=lanczos,setsar=1','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    source_audio=any(s['codec_type']=='audio' for s in before['streams'])
    audio_path=source if args.audio=='source' and source_audio else MILI if args.audio=='mili' else None
    if args.audio=='mili' and not audio_path.exists():raise FileNotFoundError(audio_path)
    # Raw video starts at its first presentation frame; preserve audio relative to it.
    audio_start=MILI_START if args.audio=='mili' else max(0,(pts[0] if pts else float(vs.get('start_time',0)))-float(before['format'].get('start_time',0))) if audio_path else 0.0
    names=['colored']+(['monochrome'] if args.diagnostic else [])
    handles=[];encoders=[];decoder=None;started=time.time();samples=[];stats=[];n=0
    try:
        dl=(out/'decode.log').open('wb');handles.append(dl)
        decoder=subprocess.Popen(decoder_cmd,stdout=subprocess.PIPE,stderr=dl)
        for name in names:
            cmd=['ffmpeg','-hide_banner','-y','-f','rawvideo','-pix_fmt','rgb24','-s',f'{args.width}x{args.height}','-r',str(fps),'-i','pipe:0']
            if audio_path:
                if audio_start:cmd+=['-ss',str(audio_start)]
                cmd+=['-i',str(audio_path),'-map','0:v:0','-map','1:a:0','-c:a','aac','-b:a','192k']
            else:cmd+=['-an']
            cmd+=['-t',str(duration),'-c:v','libx264','-preset','fast','-crf',str(args.crf),'-pix_fmt','yuv420p','-movflags','+faststart',str(out/(name+'.mp4'))]
            log=(out/(name+'_encode.log')).open('wb');handles.append(log)
            encoders.append((name,subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=subprocess.DEVNULL,stderr=log),cmd))
        (out/'processes.json').write_text(json.dumps({'state':'RUNNING','decoder_pid':decoder.pid,'encoders':{name:p.pid for name,p,cmd in encoders}},indent=2),encoding='utf8')
        sample_frames={0,max(0,round(duration*float(fps)*.25)),max(0,round(duration*float(fps)*.5)),max(0,round(duration*float(fps)*.75)),max(0,round(duration*float(fps))-1)}
        if args.sample_frames:sample_frames.update(int(x) for x in args.sample_frames.split(',') if x.strip())
        (out/'frames').mkdir(exist_ok=True)
        while True:
            raw=decoder.stdout.read(dw*dh*3)
            if not raw:break
            if len(raw)!=dw*dh*3:raise RuntimeError('Partial decoded RGB frame')
            im=Image.frombytes('RGB',(dw,dh),raw);chars,colors,detail=converter.cells(im)
            colored=converter.render(chars,colors)
            for name,p,cmd in encoders:p.stdin.write((colored if name=='colored' else converter.render(chars,colors,True)).tobytes())
            if n in sample_frames:
                fit,offset=converter.fit(im);src=Image.new('RGB',(args.width,args.height),BG);src.paste(fit,offset)
                src.save(out/'frames'/f'source_{n:05d}.png');colored.save(out/'frames'/f'glyph_{n:05d}.png');converter.render(chars,colors,True).save(out/'frames'/f'mono_{n:05d}.png')
                (out/'frames'/f'grid_{n:05d}.txt').write_text(converter.text(chars),encoding='utf8')
                samples.append((n,src.resize((960,540)),colored.resize((960,540))))
            if n%max(1,round(float(fps)*2))==0:print(f'{out.name}: frame {n}, t={n/float(fps):.3f}s',flush=True)
            stats.append(detail);n+=1
        decoder.stdout.close();assert decoder.wait(timeout=60)==0
        for name,p,cmd in encoders:p.stdin.close()
        for name,p,cmd in encoders:
            if p.wait(timeout=120)!=0:raise RuntimeError(f'Encoder {name} failed; see log')
    finally:
        for p in ([decoder] if decoder else [])+[p for _,p,_ in encoders]:
            if p.poll() is None:p.kill();p.wait()
        for handle in handles:handle.close()
        (out/'processes.json').write_text(json.dumps({'state':'TERMINATED','decoder':{'pid':decoder.pid,'returncode':decoder.returncode} if decoder else None,'encoders':{name:{'pid':p.pid,'returncode':p.returncode} for name,p,cmd in encoders}},indent=2),encoding='utf8')
    if not n:raise RuntimeError('No video frames decoded')
    sheet=Image.new('RGB',(1920,len(samples)*580),BG);draw=ImageDraw.Draw(sheet);font=ImageFont.truetype(FONT_PATH,22)
    for row,(idx,src,glyph) in enumerate(samples):
        yy=row*580;draw.text((18,yy+5),f'SOURCE | frame {idx} | {idx/float(fps):.3f}s',font=font,fill='#bed0df');draw.text((978,yy+5),'GLYPHS | same decoded frame / no crop',font=font,fill='#bed0df');sheet.paste(src,(0,yy+36));sheet.paste(glyph,(960,yy+36))
    sheet.save(out/'comparison.png')
    outputs={}
    for name,p,cmd in encoders:
        info,stream=probe(out/(name+'.mp4'));check=subprocess.run(['ffmpeg','-hide_banner','-v','error','-i',str(out/(name+'.mp4')),'-f','null','-'],capture_output=True,text=True)
        if check.returncode or check.stderr.strip():raise RuntimeError('Full output decode failed: '+check.stderr)
        video_delta=abs(float(stream['duration'])-duration)
        if video_delta>1/float(fps)+.01:raise AssertionError('Output video timing exceeds one-frame tolerance')
        if abs(int(stream['nb_frames'])-n)>1:raise AssertionError('Encoded/decoded frame count differs by more than one frame')
        if Fraction(stream['r_frame_rate'])!=fps:raise AssertionError('Unexpected output frame rate')
        if (stream['width'],stream['height'])!=(args.width,args.height):raise AssertionError('Unexpected output dimensions')
        if any(s['codec_type']=='audio' for s in info['streams'])!=bool(audio_path):raise AssertionError('Unexpected audio presence/absence')
        outputs[name]={'sha256':sha(out/(name+'.mp4')),'probe':info,'full_decode_exit':check.returncode,'full_decode_stderr':check.stderr,'video_duration_delta_seconds':video_delta,'actual_video_frames':int(stream['nb_frames'])}
    manifest={'status':'CONVERSION_SOFTWARE_PASS','content_label':args.label,'input':{'path':str(source),'sha256':sha(source),'probe':before,'duration':duration,'actual_frames':len(pts),'fps_metadata':vs.get('avg_frame_rate'),'vfr_detected':vfr},'parameters':vars(args),'timing':{'output_fps':str(fps),'decoded_frames':n,'normalized_duration':n/float(fps),'normalization':'ffmpeg fps filter at source average rate or explicit --fps; no speed change','source_pts_quantization_max_seconds':max((abs((t-pts[0])*float(fps)-round((t-pts[0])*float(fps)))/float(fps) for t in pts),default=0)},'geometry':{'source_dimensions':[int(vs['width']),int(vs['height'])],'decoded_fit_dimensions':[dw,dh],'output_dimensions':[args.width,args.height],'native_grid':[converter.cols,converter.rows],'cell_pixels':[converter.cw,converter.ch],'fit':'entire frame, centered letterbox; no crop','fit_aspect_relative_error':abs((dw/dh)/(int(vs['width'])/int(vs['height']))-1)},'audio':{'mode':args.audio,'path':str(audio_path) if audio_path else None,'trim_start_seconds':audio_start,'source_has_audio':source_audio,'music_sync':'No music synchronization or time stretching is inferred.'},'glyph_stats':converter.stats,'frame_stats_range':{'masked':[min(x['masked_cells'] for x in stats),max(x['masked_cells'] for x in stats)],'edge':[min(x['edge_cells'] for x in stats),max(x['edge_cells'] for x in stats)]},'outputs':outputs,'elapsed_seconds':time.time()-started,'owner_visual_acceptance':'PENDING','limitations':['Video glyph conversion preserves source motion; it cannot improve source dance/anatomy defects.','Automatic mask estimates border-connected background by color, not semantic segmentation; use --background none or lower tolerance if dark clothing is removed.','VFR input is normalized to output CFR without speed change; timestamps are quantized within one output frame.','Small face/hand details remain limited by glyph density.','Hysteresis only retains near-threshold non-edge glyph choices; current color/visibility/edge geometry are never temporally blended.']}
    manifest['geometry'].update(source_display_aspect=display_aspect,source_rotation_degrees=rotation,source_sample_aspect_ratio=sar,fit_aspect_relative_error=abs((dw/dh)/display_aspect-1))
    manifest['audio']['alignment']='Original source audio seeks to first video PTS relative to format origin; Mili mode instead uses its explicit fixed trim.'
    manifest['software_sha256']={name:sha(HERE/name) for name in ('convert.py',)}
    (out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
    source_url=quote(Path(os.path.relpath(source,out)).as_posix())
    (out/'index.html').write_text(review_html(args.label,names,source_url),encoding='utf8')
    print(json.dumps({'status':manifest['status'],'out':str(out),'decoded_frames':n,'outputs':{k:v['actual_video_frames'] for k,v in outputs.items()},'source_duration':duration,'vfr':vfr}),flush=True)
    return manifest

def review_html(label,names,source_url=None):
    diagnostic='<h2>单色字符诊断</h2><video controls src="monochrome.mp4"></video>' if 'monochrome' in names else ''
    source_block=f'<h2>原始舞蹈源视频</h2><video controls src="{html.escape(source_url,quote=True)}"></video>' if source_url else ''
    return f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Video → glyph review</title><style>body{{background:#07101d;color:#d7e4ef;max-width:1500px;margin:auto;padding:28px;font:16px/1.7 system-ui}}video,img{{width:100%;display:block}}video{{aspect-ratio:16/9;object-fit:contain;background:#07101d}}a{{color:#9ccbef}}p{{color:#acbfd1}}</style><h1>Video → 字符转换</h1><p>{html.escape(label)}</p>{source_block}<h2>彩色字符候选</h2><video controls src="colored.mp4"></video>{diagnostic}<h2>源视频与字符帧对照</h2><a href="comparison.png"><img src="comparison.png"></a><p><a href="manifest.json">输入哈希、时间戳、参数、音频来源与检查记录</a></p><p>整幅画面按比例适配，不裁切人物。自动背景遮罩是颜色启发式，不是语义分割。输出质量和舞蹈质量仍需原速观看；软件检查不代替视觉验收。</p></html>'''

def parser():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('input');p.add_argument('--output',required=True);p.add_argument('--preset',choices=PRESETS,default='readable');p.add_argument('--width',type=int,default=1920);p.add_argument('--height',type=int,default=1080);p.add_argument('--background',choices=('auto','dark','light','none'),default='auto');p.add_argument('--mask-tolerance',type=int,default=20);p.add_argument('--hysteresis',type=int,default=3);p.add_argument('--bright',action='store_true',help='Bold font, denser interior glyphs and brighter ink');p.add_argument('--white-pockets',type=int,default=0,help='Optional minimum RGB threshold for neutral enclosed white background');p.add_argument('--fps',help='Optional CFR rate; default source average frame rate');p.add_argument('--audio',choices=('source','none','mili'),default='source');p.add_argument('--diagnostic',action='store_true');p.add_argument('--crf',type=int,default=17);p.add_argument('--max-seconds',type=float,default=60);p.add_argument('--sample-frames',help='Additional comma-separated source-normalized frame indices; endpoint is always sampled');p.add_argument('--label',default='Video-to-glyph candidate; owner visual review pending.');return p
if __name__=='__main__':export(parser().parse_args())
