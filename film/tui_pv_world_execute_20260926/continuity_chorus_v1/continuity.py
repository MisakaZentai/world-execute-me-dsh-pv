"""Isolated chorus continuity study. Original files and sidebar caches are read-only."""
import os, sys
sys.dont_write_bytecode = True
os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
import argparse, hashlib, importlib.util, inspect, json, math, random, subprocess, time
from pathlib import Path
from functools import lru_cache
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parent
spec = importlib.util.spec_from_file_location('accepted_sidebar', PROJECT/'sidebar_chorus_v1/sidebar.py')
sb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sb)
sb.ENVELOPE = tuple(json.loads((sb.ROOT/'envelope.json').read_text())['crop'])
engine, tk, section = sb.engine, sb.tk, sb.section
import stage
FIRST, COUNT, FPS = 1300, 465, 24
START = FIRST/FPS
FULL_NAMES = {'shot_if_i_can', 'shot_happy', 'shot_strange'}
SHOTS = {s.fn.__name__:s for s in engine.SHOTS if s.end > START and s.start < (FIRST+COUNT)/FPS}
PROCESSES = json.loads((ROOT/'processes.json').read_text()) if (ROOT/'processes.json').exists() else []

def write_json(name, value):
    (ROOT/name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf8')

def inputs():
    # Hash protected code, cached data, complete old sample package, original full movie,
    # source dance, lyrics/music and artwork actually used by the original renderer.
    paths = set(sb.inputs()) | {engine.AUDIO, engine.LRC}
    paths.update(p for p in (PROJECT/'sidebar_chorus_v1').rglob('*') if p.is_file())
    paths.add(PROJECT/'video_ascii_v1/convert.py')
    for value in vars(tk).values():
        if isinstance(value, Path) and value.exists():
            if value.is_file(): paths.add(value)
            elif value.name in ('expressions','poses'): paths.update(p for p in value.rglob('*') if p.is_file())
    return sorted(paths, key=str)

def snapshot():
    return {str(p):sb.sha(p) for p in inputs()}

def event(label, command, timeout=180):
    with (ROOT/(label+'.log')).open('wb') as log:
        p = subprocess.Popen(command, stdout=log, stderr=log)
        row = dict(label=label, pid=p.pid, command=command, returncode=None)
        PROCESSES.append(row); write_json('processes.json', PROCESSES)
        try:
            rc = p.wait(timeout=timeout)
        finally:
            if p.poll() is None: p.kill(); p.wait()
            row['returncode']=p.returncode; write_json('processes.json', PROCESSES)
        assert rc == 0, label

# Adapt just two existing scenes in memory so sample #0000 and the convolution
# input genuinely share the same portrait; the kernels, six maps and labels remain.
ns = dict(vars(section))
src = inspect.getsource(section.shot_simulations).replace(
    'EXPRS[(i * 3) % len(EXPRS)]', '("starry" if i == 0 else EXPRS[(i * 3) % len(EXPRS)])').replace(
    'return ease((c.lt - starts[i] * c.dur) / (0.62 * c.dur))',
    'return 1.0 if i == 0 else ease((c.lt - starts[i] * c.dur) / (0.62 * c.dur))')
exec(compile(src, '<continuity:sample_identity>', 'exec'), ns)
src = inspect.getsource(section.shot_then_i_can).replace('"cheerful"', '"starry"').replace(
    'me_pane(c, "starry", overlay=kernel_overlay,',
    'me_pane(c, "starry", sprite_img=halfblock("starry", "full", 324, 448, 4), overlay=kernel_overlay,')
exec(compile(src, '<continuity:convolution_identity>', 'exec'), ns)
for name in ('shot_simulations', 'shot_then_i_can'):
    SHOTS[name].fn = ns[name]

def ease(v):
    v = max(0., min(1., v))
    return v*v*(3-2*v)

def mapped(rect):
    x0,y0,x1,y1=rect
    return (x0, round(56+(y0-56)*478/548), x1, round(56+(y1-56)*478/548))

def lerp_rect(a,b,u):
    return tuple(round(x+(y-x)*u) for x,y in zip(a,b))

def paste_at(im, obj, rect):
    x,y,x1,y1=rect
    obj=obj.resize((max(1,x1-x),max(1,y1-y)),Image.Resampling.LANCZOS)
    im.paste(obj,(x,y),obj if obj.mode=='RGBA' else None)

@lru_cache(24)
def sample_object():
    tile=Image.new('RGB',(178,144),tk.BG)
    d=ImageDraw.Draw(tile)
    d.rectangle((0,0,177,143),outline=tk.blue(.9))
    art=section.diffusion_tile('starry','upper',166,122,3,1.)
    tile.paste(art,((178-art.width)//2,142-art.height),art)
    d.text((6,4),'#0000 t=000',font=tk.font(tk.F_MONO,12),fill=tk.blue(.95))
    return tile

@lru_cache(24)
def vector_object():
    im=Image.new('RGB',(720,22),tk.BG); d=ImageDraw.Draw(im); rr=random.Random(78)
    for q in range(60): tk.heat_cell(d,q*12,0,12,22,rr.random(),tk.AMBER)
    return im

def chip(im, text, rect, color=None, size=19):
    color=color or tk.blue(.95); d=ImageDraw.Draw(im); x,y,x1,y1=rect
    d.rectangle(rect,fill=tk.BG,outline=color,width=2)
    f=tk.font(tk.F_MONO_B,size)
    d.text((x+(x1-x-d.textlength(text,font=f))/2,y+(y1-y-size)/2-1),text,font=f,fill=color)

SAMPLE_HOME=(414,549,480,603)
VECTOR_HOME=(516,567,946,589)
ONLY_HOME=(1038,582,1154,604)
YOU_HOME=(916,572,1018,600)

def raw(t,index,shot):
    body=sb.body(t,index,shot)
    return body

def body_image(body, name):
    canvas=body['canvas']
    if name in FULL_NAMES: return canvas.copy()
    out=canvas.copy()
    d=ImageDraw.Draw(out); d.rectangle((404,56,1164,604), fill=tk.BG)
    out.paste(canvas.crop(engine.CENTER).resize((760,478),Image.Resampling.LANCZOS),(404,56))
    d=ImageDraw.Draw(out)
    d.line((404,543,1164,543),fill=tk.amb(.26))
    return out

def retained_objects(im, t, name, c):
    d=ImageDraw.Draw(im)
    sim,conv,sat,happy,exe,trap,strange=[SHOTS['shot_'+n] for n in
        ('simulations','then_i_can','satisfaction','happy','execution','trapped','strange')]
    # The first candidate is physically pulled out of the candidate grid into
    # an input dock; it persists without changing pose/color through convolution.
    if sim.start <= t < sat.start+.32:
        if t < conv.start:
            u=ease((t-(sim.end-.48))/.48)
            if u>0:
                source=mapped((414,70,592,214))
                d.rectangle(source,fill=tk.BG,outline=tk.blue(.18))
                paste_at(im,sample_object(),lerp_rect(source,SAMPLE_HOME,u))
        else:
            paste_at(im,sample_object(),SAMPLE_HOME)
        if t>=sim.end-.48:
            d.text((490,549),'#0000 / input',font=tk.font(tk.F_MONO,12),fill=tk.blue(.8))
        if conv.start <= t < conv.end:
            d.line((480,576,496,576,496,534),fill=tk.blue(.55))
    # Lift the exact seeded final flatten vector, then feed it into the incoming
    # attention matrix. The incoming scan is attached to the vector's endpoint.
    if conv.end-.42 <= t < sat.start+.42:
        if t < sat.start:
            u=ease((t-(conv.end-.42))/.42)
            source=mapped((420,532,1140,554))
            d.rectangle(source,fill=tk.BG)
            dest=lerp_rect(source,VECTOR_HOME,u)
        else:
            u=ease((t-sat.start)/.42)
            dest=lerp_rect(VECTOR_HOME,mapped((470,110,758,132)),u)
        paste_at(im,vector_object(),dest)
        d.text((650,549),'flatten -> attention',font=tk.font(tk.F_MONO,12),fill=tk.amb(.85))
    # Pull the selected output from the actual probability panel, then retain it
    # independently of the target YOU. The lower-right position survives happy.
    only_start=sat.start+.55*(sat.end-sat.start)
    if only_start <= t < strange.start:
        u=ease((t-only_start)/.42)
        source=mapped((800,359,966,405))
        if t < sat.end:
            d.rectangle(source,fill=tk.BG)
        pos=lerp_rect(source,ONLY_HOME,u)
        chip(im,'ONLY',pos,size=15 if u>.85 else 25)
        if name=='shot_satisfaction' and u>.95:
            d.line((1096,572,1096,534),fill=tk.blue(.7))
        if name=='shot_execution':
            d.line((1096,572,1096,530),fill=tk.blue(.5))
            if .55<c.u<.80:
                d.rectangle((1028,563,1161,604),outline=tk.red(.98),width=2)
    # YOU comes from OBSERVE's existing reference, then is pinned into cache.
    if exe.start+.32 <= t < strange.start+.50:
        u=ease((t-(exe.start+.32))/.72)
        pos=lerp_rect(mapped((970,155,1090,184)),YOU_HOME,u)
        chip(im,'YOU',pos,tk.blue(.95),size=17)
        if t>=trap.start:
            px,py=520,mapped((0,141,0,141))[1]
            d.line((958,572,958,522,px,522,px,py+17),fill=tk.blue(.45))
            d.rectangle((px-5,py-4,px+18,py+19),outline=tk.blue(.9),width=2)
            d.text((778,549),'pinned / evict denied',font=tk.font(tk.F_MONO,12),fill=tk.blue(.8))
    if name=='shot_unite' and c.u>.65:
        chip(im,'we',(694,562,774,597),tk.amb(.95))
    elif name=='shot_deeply' and c.lt<.8:
        u=ease(c.lt/.8)
        chip(im,'we',lerp_rect((694,562,774,597),(458,85,516,113),u),tk.amb(.95),16)

def render_frame(n):
    t=n/FPS; shot=engine.shot_at(t); name=shot.fn.__name__
    body=raw(t,n,shot); c=body['ctx']; im=body_image(body,name)
    if c.black: return engine.post(im,None)
    ordered=list(SHOTS.values()); at=ordered.index(shot) if shot in ordered else -1
    # Two fullscreen handoffs use actual artwork as the travelling object.
    # The IF I CAN glyph portrait contracts, then only that local object resolves
    # into the same-identity halfblock candidate. No whole-screen crossfade.
    if name=='shot_simulations' and c.lt<.46:
        prev=SHOTS['shot_if_i_can']
        before=raw(prev.end-1/FPS,round(prev.end*FPS)-1,prev)['canvas']
        portrait=before.crop((288,82,912,594))
        dest=mapped((414,70,592,214))
        u=ease(min(1.,c.lt/.36))
        rect=lerp_rect((288,82,912,594),dest,u)
        if c.lt>.32:
            local=ease((c.lt-.32)/.14)
            target=sample_object().resize(portrait.size,Image.Resampling.LANCZOS)
            portrait=Image.blend(portrait,target,local)
        ImageDraw.Draw(im).rectangle(dest,fill=tk.BG)
        paste_at(im,portrait,rect)
    # On happy, her actual outgoing sidebar head grows into the large closeup.
    # Render-style resolution is confined to the moving face itself. Policy and
    # objective panels enter in place; the selected ONLY token is redrawn later.
    if name=='shot_happy' and c.lt<.42:
        prev=SHOTS['shot_satisfaction']
        before=body_image(raw(prev.end-1/FPS,round(prev.end*FPS)-1,prev),'shot_satisfaction')
        im.paste(before.crop((24,56,700,604)),(24,56))
        u=ease(c.lt/.42)
        rect=lerp_rect((116,92,268,226),(24,56,700,604),u)
        old_face=before.crop((116,92,268,226))
        happy_face=body['canvas'].crop((24,56,700,604))
        local=ease((c.lt-.12)/.22)
        obj=Image.blend(old_face.resize(happy_face.size,Image.Resampling.LANCZOS),happy_face,local)
        paste_at(im,obj,rect)
    # Different boundaries have different jobs. Ordinary workspaces update by
    # content bands; sample/vector/token overlays remain outside this operation.
    scan_names={'shot_deeply','shot_then_i_can','shot_satisfaction','shot_execution','shot_trapped'}
    if name in scan_names and c.lt<.26 and at>0:
        prev=ordered[at-1]
        before=body_image(raw(prev.end-1/FPS,round(prev.end*FPS)-1,prev),prev.fn.__name__)
        u=ease(c.lt/.26)
        if name=='shot_then_i_can':
            # Kernel/receptive field open first; previous candidates remain below.
            y=round(56+478*u); im.paste(before.crop((404,y,1164,534)),(404,y))
            ImageDraw.Draw(im).line((404,y,1164,y),fill=tk.blue(.65))
        elif name=='shot_satisfaction':
            # Attention opens from the left while probability/reward settles after.
            x=round(404+760*u); im.paste(before.crop((x,56,1164,534)),(x,56))
        elif name=='shot_trapped':
            # Cache allocates in rows, retaining the tool result below the frontier.
            y=round(56+478*u); im.paste(before.crop((404,y,1164,534)),(404,y))
        elif name=='shot_deeply':
            y=round(56+478*u); im.paste(before.crop((404,y,1164,534)),(404,y))
        else:
            # Tool panel expands upward; the outgoing happy view stays visible above.
            y=round(534-478*u); im.paste(before.crop((404,56,1164,y)),(404,56))
    # Pin-origin failure: cache remains visible while a corruption front grows
    # from the SAME retained YOU block, before the original strange fills screen.
    if name=='shot_strange' and c.lt<.58:
        prev=SHOTS['shot_trapped']
        old=body_image(raw(prev.end-1/FPS,round(prev.end*FPS)-1,prev),'shot_trapped')
        oc=raw(prev.end-1/FPS,round(prev.end*FPS)-1,prev)['ctx']
        retained_objects(old,prev.end-1/FPS,'shot_trapped',oc)
        mask=Image.new('L',im.size,0); md=ImageDraw.Draw(mask)
        radius=18+1320*ease(c.lt/.58); px,py=520,mapped((0,141,0,141))[1]
        md.ellipse((px-radius,py-radius,px+radius,py+radius),fill=255)
        im=Image.composite(im,old,mask)
        dd=ImageDraw.Draw(im)
        dd.ellipse((px-radius,py-radius,px+radius,py+radius),outline=tk.red(.7),width=2)
        if c.lt<.32: chip(im,'NaN',(px-20,py-8,px+62,py+24),tk.red(1.),18)
    retained_objects(im,t,name,c)
    c.img,c.d=im,ImageDraw.Draw(im)
    # Fixed chrome and lyric geometry. Strong red stays local to execute banner;
    # corruption retains its original red/fullscreen semantics.
    engine.header(c); engine.ticker(c); engine.lyric_tokens(c)
    return engine.post(im,None)

def preflight():
    out=ROOT/'preflight'; out.mkdir(exist_ok=True)
    times=[55.8,57.25,59.8,62.10,62.42,63.45,64.35,64.65,65.7,67.3,69.25,70.25,71.30,71.50,71.77,72.4]
    sheet=Image.new('RGB',(1280,4*390),tk.BG);d=ImageDraw.Draw(sheet)
    for j,t in enumerate(times):
        n=round(t*FPS);im=render_frame(n);im.save(out/f'{n:04d}.png')
        x=(j%4)*320;y=(j//4)*390
        sheet.paste(im.resize((320,180)),(x,y+28))
        # Larger, meaningful lower main-panel crop shows object continuity.
        sheet.paste(im.crop((404,410,1164,604)).resize((320,82)),(x,y+218))
        d.text((x+6,y+7),f'{n/FPS:.3f} {engine.shot_at(n/FPS).fn.__name__[5:]}',fill=tk.amb(.95))
    sheet.save(out/'contact_sheet.png')
    # Focused boundary strips for the two corrected fullscreen handoffs.
    rows=[('portrait_to_sample',[60.60,60.68,60.85,61.00,61.10]),
          ('sidebar_to_happy',[66.125,66.20,66.33,66.46,66.625])]
    boundary=Image.new('RGB',(1600,2*210),tk.BG);bd=ImageDraw.Draw(boundary)
    for row,(label,ts) in enumerate(rows):
        for col,t in enumerate(ts):
            n=round(t*FPS);im=render_frame(n);im.save(out/f'{n:04d}.png')
            boundary.paste(im.resize((320,180)),(col*320,row*210+24))
            bd.text((col*320+6,row*210+5),f'{label} / {n/FPS:.3f}',fill=tk.amb(.95))
    boundary.save(out/'fullscreen_handoffs.png')
    write_json('scene_map.json',[dict(name=s.fn.__name__,start=s.start,end=s.end) for s in SHOTS.values()])
    write_json('preflight_dance_calls.json',sb.CALLS);sb.CALLS.clear()
    print(str(out/'contact_sheet.png'),flush=True)

def render():
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','24','-i','pipe:0',
         '-ss',str(START),'-i',str(engine.AUDIO),'-map','0:v','-map','1:a','-t',str(COUNT/FPS),
         '-c:v','libx264','-preset','fast','-crf','17','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k',
         '-movflags','+faststart',str(ROOT/'continuity_chorus.mp4')]
    with (ROOT/'render.log').open('wb') as log:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=log)
        row=dict(label='encode',pid=p.pid,command=cmd,returncode=None)
        PROCESSES.append(row);write_json('processes.json',PROCESSES)
        try:
            for k in range(COUNT):
                im=render_frame(FIRST+k);p.stdin.write(im.tobytes())
                if k%48==0: print(f'frame {k}/{COUNT}',flush=True)
            p.stdin.close();assert p.wait(timeout=120)==0
        finally:
            if p.poll() is None: p.kill();p.wait()
            row['returncode']=p.returncode;write_json('processes.json',PROCESSES)
    write_json('dance_mapping.json',sb.CALLS)

def verify():
    event('ffprobe',['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(ROOT/'continuity_chorus.mp4')])
    data=json.loads((ROOT/'ffprobe.log').read_text());write_json('metadata.json',data)
    video=next(s for s in data['streams'] if s['codec_type']=='video')
    audio=next(s for s in data['streams'] if s['codec_type']=='audio')
    assert (video['width'],video['height'],video['r_frame_rate'],int(video['nb_frames']))==(1280,720,'24/1',465)
    assert abs(float(video['duration'])-19.375)<.002
    assert abs(float(audio['duration'])-19.375)<.03
    event('full_decode',['ffmpeg','-v','error','-xerror','-i',str(ROOT/'continuity_chorus.mp4'),'-map','0:v','-map','0:a','-f','null','-'])
    old=json.loads((ROOT/'input_hashes.json').read_text());new=snapshot()
    changed=[p for p,h in old.items() if new.get(p)!=h]
    assert not changed,changed
    write_json('validation.json',dict(status='PASS',exercised_scope='465 video frames and complete audio decoded; metadata, protected inputs, accepted native glyph mapping',
        video_frames=465,video_seconds=19.375,protected_files=len(old),changed_inputs=changed,
        ordinary_sidebar_native_size=True,source_span=[54,159],visual_acceptance='PENDING parent/user review',
        processes_returned=all(p['returncode']==0 for p in PROCESSES)))
    print('PASS: metadata, complete A/V decode and protected-input hashes',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--render',action='store_true');ap.add_argument('--verify',action='store_true');a=ap.parse_args()
    if not (ROOT/'input_hashes.json').exists(): write_json('input_hashes.json',snapshot())
    if a.preflight: preflight()
    if a.render: render()
    if a.verify: verify()
