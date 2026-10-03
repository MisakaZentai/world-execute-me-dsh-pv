"""Original anchored TUI, with native-size glyph video only in ordinary sidebar panes."""
import os,sys,json,math,hashlib,subprocess,argparse,importlib.util
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageChops
ROOT=Path(__file__).resolve().parent;PROJECT=ROOT.parent
os.environ.update(TUI_PALETTE='deepsea',TUI_ANCHOR='1',TUI_DANCE='1',TUI_FOCUS='0',PYTHONDONTWRITEBYTECODE='1')
sys.dont_write_bytecode=True
sys.path.insert(0,str(PROJECT/'full'))
import engine,build,dancer,tuikit as tk,music,sec_chorus1 as section
assert music.CACHE.exists(),'Original read-only music cache is required'
music.table() # Populate only from existing cache; never recompute/write.
spec=importlib.util.spec_from_file_location('sidebar_converter',PROJECT/'video_ascii_v1/convert.py');cv=importlib.util.module_from_spec(spec);spec.loader.exec_module(cv)
cv.PRESETS['sidebar']=(3,5,5)
SOURCE=PROJECT/'video_ascii_v1/sources/whale_maid_updream_dance_v2_752x560_24fps_silent.mp4'
BASELINE=PROJECT/'full/tui_pv_full_deepsea_anchor.mp4'
FIRST=1300;COUNT=465;FPS=24;START=FIRST/FPS
ALLOWED={'shot_deeply':54,'shot_satisfaction':96,'shot_execution':54,'shot_trapped':112}
CALLS=[];CURRENT=None;KW={};ENVELOPE=None
PROCESSES=json.loads((ROOT/'processes.json').read_text()) if (ROOT/'processes.json').exists() else []
def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()
def record(): (ROOT/'processes.json').write_text(json.dumps(PROCESSES,indent=2),encoding='utf8')
def run(command,label):
    with (ROOT/(label+'.log')).open('wb') as log:
        p=subprocess.Popen(command,stdout=log,stderr=log);entry=dict(label=label,pid=p.pid,returncode=None);PROCESSES.append(entry);record()
        try:code=p.wait(timeout=240)
        finally:
            if p.poll() is None:p.kill();p.wait()
            entry['returncode']=p.returncode;record()
        assert code==0,label
def inputs():return [PROJECT/'tuikit.py',SOURCE,BASELINE]+list((PROJECT/'full').glob('*.py'))+[music.CACHE]+list((PROJECT/'full/poses').glob('*.txt'))
def prep():
    global ENVELOPE
    cache=ROOT/'source_frames';cache.mkdir(exist_ok=True)
    if len(list(cache.glob('*.png')))!=106:run(['ffmpeg','-v','error','-y','-i',str(SOURCE),'-vf','select=between(n\\,54\\,159)','-fps_mode','passthrough','-start_number','54',str(cache/'%04d.png')],'source_extract')
    boxes=[]
    for path in cache.glob('*.png'):
        im=Image.open(path).convert('RGB');diff=ImageChops.difference(im,Image.new('RGB',im.size,'white'));r,g,b=diff.split();m=ImageChops.lighter(ImageChops.lighter(r,g),b).point(lambda x:255 if x>40 else 0);boxes.append(m.getbbox())
    ENVELOPE=(max(0,min(x[0] for x in boxes)-8),max(0,min(x[1] for x in boxes)-8),min(752,max(x[2] for x in boxes)+8),min(560,max(x[3] for x in boxes)+8))
    (ROOT/'envelope.json').write_text(json.dumps(dict(crop=ENVELOPE,source_frames=[54,159],rule='Union of source pixels >40 away from white, expanded8px; fixed for all shots'),indent=2),encoding='utf8')
    if not (ROOT/'input_hashes.json').exists():(ROOT/'input_hashes.json').write_text(json.dumps({str(p):sha(p) for p in inputs()},indent=2),encoding='utf8')
@lru_cache(512)
def glyph(source,width,height,tint):
    im=Image.open(ROOT/'source_frames'/f'{source:04d}.png').convert('RGB').crop(ENVELOPE)
    c=cv.Converter(width,height,'sidebar','auto',20,0,True,247)
    chars,colors,detail=c.cells(im)
    out=Image.new('RGBA',(width,height));d=ImageDraw.Draw(out)
    # Readable cold blue ink, while retaining the source luminance and glyph contours.
    ramp=dancer._ramp(tint)
    for i,ch in enumerate(chars):
        if ch==' ':continue
        rgb=colors[i];lum=round(sum(rgb)/3);color=ramp[max(110,min(245,lum))]
        d.text(((i%c.cols)*3,(i//c.cols)*5-1),ch,font=c.font,fill=(*color,255))
    return out
ORIGINAL_RENDER=dancer.render;ORIGINAL_PANE=section.me_pane;ORIGINAL_BODY=engine.render_body
def body(t,index,shot):
    global CURRENT
    old=CURRENT;CURRENT=shot
    try:return ORIGINAL_BODY(t,index,shot)
    finally:CURRENT=old
def pane(c,expr,*args,**kwargs):
    global KW
    old=KW;KW=kwargs
    try:return ORIGINAL_PANE(c,expr,*args,**kwargs)
    finally:KW=old
def replacement(t,size,expr,*args,**kwargs):
    name=CURRENT.fn.__name__ if CURRENT else ''
    if name not in ALLOWED:return ORIGINAL_RENDER(t,size,expr,*args,**kwargs)
    source=min(159,max(54,ALLOWED[name]+int(math.floor((t-CURRENT.start)*24+1e-6))))
    width=max(12,size[0]-12);reserve=150 if name=='shot_deeply' else 0
    height=max(20,size[1]-reserve-10);tint=args[1] if len(args)>1 else kwargs.get('tint','blue')
    art=glyph(source,width,height,tint);out=Image.new('RGBA',(size[0],height));out.alpha_composite(art,(6,0))
    rect=KW.get('rect',engine.LEFT);dy=KW.get('dy',0);bottom=rect[3]-(78 if KW.get('dist') else 6)
    bbox=out.getbbox();world=None if bbox is None else [bbox[0]+rect[0]+4,bbox[1]+rect[1]+14+dy,bbox[2]+rect[0]+4,bbox[3]+rect[1]+14+dy]
    assert world and world[0]>=rect[0]+2 and world[2]<=rect[2]-2 and world[1]>=rect[1]+12 and world[3]<=bottom,(name,world,rect,bottom)
    CALLS.append(dict(time=t,shot=name,source_frame=source,canvas=list(out.size),rect=list(rect),dy=dy,visible_bbox=world,bottom=bottom))
    return out,None
engine.render_body=body;section.me_pane=pane;dancer.render=replacement
def stills():
    out=ROOT/'preflight';out.mkdir(exist_ok=True);times=[57.7,59.9,63.2,65.2,70.7]
    sheet=Image.new('RGB',(1280,len(times)*386),tk.BG);d=ImageDraw.Draw(sheet)
    for j,t in enumerate(times):
        n=round(t*24);im=engine.render_frame(n/24,None,n);im.save(out/f'{t:.2f}.png');sheet.paste(im.resize((640,360)),(0,j*386+24));d.text((8,j*386+4),f'{n/24:.3f}s / {engine.shot_at(n/24).fn.__name__}',fill=(220,230,245));d.text((660,j*386+100),'Original renderer + ordinary sidebar hook only',fill=(170,200,235))
    sheet.save(out/'contact_sheet.png')
    (ROOT/'preflight_calls.json').write_text(json.dumps(CALLS,indent=2),encoding='utf8');CALLS.clear()
def render():
    command=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','24','-i','pipe:0','-ss',str(START),'-i',str(engine.AUDIO),'-map','0:v','-map','1:a','-t',str(COUNT/24),'-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(ROOT/'sidebar_chorus.mp4')]
    with (ROOT/'render.log').open('wb') as log:
        p=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=log);entry=dict(label='sidebar_encode',pid=p.pid,returncode=None);PROCESSES.append(entry);record()
        try:
            prev=None;previous_shot=None
            for k in range(COUNT):
                n=FIRST+k;t=n/24;shot=engine.shot_at(t);im=engine.render_frame(t,prev if shot is previous_shot else None,n,shot);prev=im;previous_shot=shot;p.stdin.write(im.tobytes())
                if k%48==0:print(f'frame {k}/{COUNT} {shot.fn.__name__}',flush=True)
            p.stdin.close();assert p.wait(timeout=120)==0
        finally:
            if p.poll() is None:p.kill();p.wait()
            entry['returncode']=p.returncode;record()
    (ROOT/'dance_mapping.json').write_text(json.dumps(CALLS,indent=2),encoding='utf8')
    baseline()
def baseline():
    run(['ffmpeg','-v','error','-y','-i',str(BASELINE),'-vf',f'trim=start_frame={FIRST}:end_frame={FIRST+COUNT},setpts=PTS-STARTPTS','-af',f'atrim=start={START}:end={(FIRST+COUNT)/24},asetpts=PTS-STARTPTS','-t',str(COUNT/24),'-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-movflags','+faststart',str(ROOT/'baseline_excerpt.mp4')],'baseline_frame_exact')
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--render',action='store_true');a=ap.parse_args();prep();stills()
    if a.render:render()
