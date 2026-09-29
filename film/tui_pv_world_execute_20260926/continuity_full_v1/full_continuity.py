"""Full-song continuity director preview. All imported packages are read-only."""
import os,sys
sys.dont_write_bytecode=True
os.environ['PYTHONDONTWRITEBYTECODE']='1'
import argparse,hashlib,importlib.util,inspect,json,math,random,subprocess,time,traceback
from pathlib import Path
from functools import lru_cache
from PIL import Image,ImageDraw,ImageOps,ImageChops

ROOT=Path(__file__).resolve().parent; PROJECT=ROOT.parent
spec=importlib.util.spec_from_file_location('approved_chorus',PROJECT/'continuity_chorus_v1/continuity.py')
approved=importlib.util.module_from_spec(spec);spec.loader.exec_module(approved)
engine,tk,sb=approved.engine,approved.tk,approved.sb
import direction,stage,transitions
FPS=24; COUNT=5064; DURATION=211.; VIDEO='tui_pv_full_continuity.mp4'
ALL=list(engine.SHOTS); INDEX={id(s):i for i,s in enumerate(ALL)}
BYNAME={s.fn.__name__:s for s in ALL}
ORIGINAL_LAYOUT=direction.layout
ORIGINAL_LAYOUTS={id(s):ORIGINAL_LAYOUT(s) for s in ALL}
CHORUS_NAMES=set(approved.SHOTS)
# The darker callback uses the SAME resolved sample0 identity as the accepted
# first chorus, while retaining its original red crosses and angry special pose.
import sec_final
callback_ns=dict(vars(sec_final))
callback_ns['shot_then_i_can']=BYNAME['shot_then_i_can'].fn
callback_src=inspect.getsource(sec_final.shot_execute_all).replace(
    'EXPRS[(i * 3) % len(EXPRS)]','("starry" if i == 0 else EXPRS[(i * 3) % len(EXPRS)])')
exec(compile(callback_src,'<full:callback_sample_identity>','exec'),callback_ns)
exec(compile(inspect.getsource(sec_final.shot_red_then_i_can),'<full:callback_convolution>','exec'),callback_ns)
BYNAME['shot_execute_all'].fn=callback_ns['shot_execute_all']
BYNAME['shot_red_then_i_can'].fn=callback_ns['shot_red_then_i_can']
KEEP_STAGE={'shot_power','shot_protection','shot_parameters','shot_limit','shot_god','shot_completion',
            'shot_you_left','shot_memory_ls','shot_challenge_god','shot_answer_all','shot_exec_hit',
            'shot_count','shot_collapse','shot_whale_fall','shot_last_execution','shot_black'}

def layout(s):
    name=s.fn.__name__;mode,kind,extra=ORIGINAL_LAYOUTS[id(s)]
    if name in CHORUS_NAMES or name in KEEP_STAGE:return mode,kind,extra
    # FULL paintings remain FULL: only incidental desktop/tmux/mirror placement is removed.
    return 'split',kind,{}
direction.layout=layout

def write_json(name,value):
    (ROOT/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def protected_inputs():
    paths=set(approved.inputs())
    paths.update(p for p in (PROJECT/'continuity_chorus_v1').rglob('*') if p.is_file())
    # Full protected original source/cache/poses, plus accepted package/source/artwork.
    paths.update(p for p in (PROJECT/'full').rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    return sorted(paths,key=str)

def snapshot():return {str(p):sha(p) for p in protected_inputs()}

def ease(v):return approved.ease(v)
def lerp(a,b,u):return approved.lerp_rect(a,b,u)
def paste(im,obj,rect):return approved.paste_at(im,obj,rect)

# Checked against actual source drawing coordinates, not merely old CHOREO comments.
# Each object is a crop of the outgoing scene. It travels into an actual destination
# object/panel and resolves locally into that panel, preserving source ink during travel.
# name: (source rectangle, destination rectangle, description, travel seconds)
HANDOFFS={
 'shot_creation':((48,440,700,506),(430,430,1082,496),'loaded weight shard / parameter result enters object fields',.65),
 'shot_parameters':((430,90,900,418),(430,82,900,410),'constructed object fields become config fields',.58),
 'shot_init':((430,520,1130,558),(430,80,1130,118),'parameter count becomes initialized weight workspace',.58),
 'shot_begin_sim':((430,566,1080,599),(460,392,1110,425),'world population/result enters simulation status',.65),
 'shot_corpus':((460,432,1140,466),(430,562,1110,596),'simulation token budget continues into corpus counter',.65),
 'shot_losscurve':((430,560,1120,598),(440,362,1130,400),'corpus counter carries to loss endpoint',.64),
 'shot_dualpipe':((1010,323,1140,400),(60,110,190,187),'loss endpoint enters first pipeline batch',.65),
 'shot_dimension':((290,100,898,570),(74,78,350,500),'point portrait contracts into native character input',.62),
 'shot_circle':((790,90,1126,116),(440,104,580,130),'delivered vector cells enter rotating pair',.58),
 'shot_circumference':((440,100,580,240),(480,120,720,360),'actual first RoPE circle enlarges into unrolling circumference',.6),
 'shot_sine':((440,434,1120,448),(430,234,1110,248),'unrolled blue line becomes selected positional channel',.55),
 'shot_tangent':((430,214,1150,266),(60,180,1140,480),'verified blue i=2 channel expands into sine/tangent stage',.6),
 'shot_limit':((430,190,1130,260),(430,190,1060,290),'growing context bar reaches its limit wall',.55),
 'shot_blind':((430,100,1140,290),(430,100,1140,290),'signal remains while causal mask closes over it',.52),
 'shot_unite':((430,330,1140,382),(430,338,1140,390),'position-id history moves into embedding workspace',.5),
 'shot_nutrients':((430,420,850,468),(456,92,876,140),'classified me=eggplant enters nutrition serving result',.62),
 'shot_antioxidants':((440,80,980,500),(850,82,1120,292),'generated tomato remains as graph input',.7),
 'shot_purr':((430,322,710,466),(430,80,710,224),'classified cat result enters its purr spectrogram',.6),
 'shot_proof':((460,428,760,456),(450,312,750,340),'process YOU moves into proof witness',.75),
 'shot_fp8':((450,340,800,373),(440,280,790,313),'proof result handed to next representation workspace',.55),
 'shot_completion':((430,346,468,378),(1088,560,1126,592),'selected YOU key remains through completion',.62),
 'shot_erase':((430,354,1100,392),(150,480,820,518),'last-message file enters optical fragment compression',.6),
 'shot_disheartened':((430,210,1120,290),(430,514,1120,594),'mutated reward rows remain under the disabled exit',.7),
 'shot_illegal':((450,452,1120,490),(430,150,1100,188),'overwritten user-ownership prompt becomes leave exception',.62),
 'shot_moe_dense':((430,116,1120,185),(50,452,740,521),'actual exception remains beside experts as failure spreads',.7),
 'shot_sinkhorn':((220,116,248,146),(460,100,564,184),'one active expert expands into residual mixing cell',.62),
 'shot_hoard':((460,476,1030,507),(60,189,630,220),'diverging residual result enters cache-hoarding workspace',.65),
 'shot_red_then_i_can':((414,70,592,234),(424,420,548,534),'crossed sample0 survives into red convolution callback',.62),
 'shot_have_you_back':((430,110,620,148),(940,540,1130,578),'selected execution result survives checkpoint restoration',.62),
 'shot_run_again':((430,400,1000,455),(430,304,1000,359),'YOU not found remains above repeated execute banner',.68),
 'shot_red_trapped':((430,152,1090,186),(424,510,1084,544),'have-you-back target remains at the pinned cache label',.6),
 'shot_learn_love':((424,168,600,252),(924,84,1100,168),'rewarded YOU answer remains beside love probability curve',.65),
 'shot_question_me':((1000,70,1140,115),(1000,90,1140,135),'learned love probability enters evaluation result column',.65),
 'shot_answer_all':((700,454,1110,490),(730,560,1140,596),'completed evaluation result survives into answer stream',.6),
 'shot_algebra':((840,80,904,108),(492,393,590,436),'actual love answer gathers into love=you formula',.65),
 'shot_you_free':((548,390,685,436),(690,318,827,364),'formula YOU becomes the departing process',.65),
 'shot_love_loop':((800,278,1160,310),(48,90,408,122),'wait-for-you result enters next-token loop',.65),
}

# Existing clearly motivated transformations retained. Generic reflow/glide is not.
KEEP_TRANSITIONS={('shot_protection','shot_pieces'),('shot_dualpipe','shot_whale'),
 ('shot_whale','shot_points'),('shot_blind','shot_dizzy'),('shot_dizzy','shot_travel'),
 ('shot_tangent','shot_infinity'),('shot_role','shot_trance'),
 ('shot_you_left','shot_isolation'),('shot_isolation','shot_memory_ls'),
 ('shot_hoard','shot_flood'),('shot_exec_hit','shot_red_if_i_can'),
 ('shot_red_if_i_can','shot_execute_all'),('shot_collapse','shot_grpo')}

def raw(t,n,s):
    body=sb.body(t,n,s)
    # Clip full paintings at their intended viewport before chrome; retain raw art.
    if body['kind']=='full' and body['mode']!='raw' and not body['black']:
        clipped=stage.background(t)
        clipped.paste(body['canvas'].crop(engine.FULL),(24,56))
        body['canvas']=clipped;body['ctx'].img=clipped;body['ctx'].d=ImageDraw.Draw(clipped)
    return body

@lru_cache(90)
def endpoint(i):
    s=ALL[i];n=math.ceil(s.end*FPS)-1
    body=raw(n/FPS,n,s)
    # Keep actual artwork before chrome and transform source crops with its stage.
    canvas=body['canvas'].copy()
    img=engine.finish(body)
    return canvas,img

def rect_screen(rect,s):
    mode,kind,extra=layout(s)
    if stage.identity(mode,kind):return rect
    return tuple(round(x) for x in stage.to_screen(rect,stage.geometry(mode,kind,extra)))

def handoff(im,t,s):
    name=s.fn.__name__;i=INDEX[id(s)]
    if name not in HANDOFFS or i==0:return
    source,dest,desc,dur=HANDOFFS[name]
    lt=t-s.start
    # Hold endpoint briefly before releasing to the incoming live computation.
    if not 0<=lt<dur+.30:return
    prev=ALL[i-1];canvas,old=endpoint(i-1)
    src=rect_screen(source,prev);dst=rect_screen(dest,s)
    obj=old.crop(src);u=ease(lt/dur);rect=lerp(src,dst,u)
    if lt>dur-.13:
        target=im.crop(dst).resize(obj.size,Image.Resampling.LANCZOS)
        obj=Image.blend(obj,target,ease((lt-(dur-.13))/.43))
    paste(im,obj,rect)

def local_update(im,t,s):
    """Local panel replacements on ordinary boundaries; no reflow particles."""
    name=s.fn.__name__;i=INDEX[id(s)];lt=t-s.start
    if i==0 or lt>=.22 or name in KEEP_STAGE or name in CHORUS_NAMES:return
    old_s=ALL[i-1];mode,kind,_=layout(s);omode,okind,_=layout(old_s)
    if kind!='split' or okind!='split' or old_s.fn.__name__ in CHORUS_NAMES:return
    if (old_s.fn.__name__,name) in KEEP_TRANSITIONS:return
    _,old=endpoint(i-1)
    # Update actual working regions one after another, not the entire body at once.
    regions=[(404,56,1164,306),(404,306,1164,604)]
    if i%2:regions.reverse()
    for j,r in enumerate(regions):
        a=.04+j*.08
        if lt<a:im.paste(old.crop(r),r[:2])
        elif lt<a+.10:
            x0,y0,x1,y1=r;p=ease((lt-a)/.10)
            x=round(x0+(x1-x0)*p)
            if x<x1:im.paste(old.crop((x,y0,x1,y1)),(x,y0))

def you_reference(im,t,s):
    name=s.fn.__name__
    if name not in {'shot_completion','shot_you_left','shot_isolation'}:return
    origin=INDEX[id(BYNAME['shot_feel_you'])]
    canvas,_=endpoint(origin);tile=canvas.crop((430,346,468,378)).convert('RGBA')
    rect=(1088,560,1126,592)
    if name=='shot_completion' and t<s.start+.62:return # handled by moving selection
    if name=='shot_you_left':
        k=s.params.get('k',0);fade=max(.12,1-(k+(t-s.start)/(s.end-s.start))*.16)
        tile=tk.scale_alpha(tile,fade)
    elif name=='shot_isolation':
        u=ease((t-s.start)/.65);rect=lerp(rect,(904,226,942,258),u)
        tile=tk.scale_alpha(tile,max(.12,1-(t-s.start)/(s.end-s.start)))
    paste(im,tile,rect)
    d=ImageDraw.Draw(im)
    if name!='shot_isolation':
        # A connection tether whose continuity survives the deliberate UI retraction.
        color=tk.amb(.32 if name=='shot_completion' else .14)
        d.line((1040,576,rect[0]-3,576),fill=color)
        if name=='shot_you_left':d.line((1055,570,1065,582),fill=tk.anom(.65),width=2)

def reward_reference(im,t,s):
    name=s.fn.__name__
    if name not in {'shot_rewrite_reward','shot_disheartened','shot_challenge_god'}:return
    origin=INDEX[id(BYNAME['shot_rewrite_reward'])]
    if name=='shot_rewrite_reward':return # original rows remain at their actual source
    if name=='shot_disheartened' and t<s.start+1.:return
    canvas,_=endpoint(origin)
    obj=canvas.crop((430,210,1120,290))
    # Same reward lines remain visible under exit denial. They depart into the
    # incoming system-prompt panel, then resolve locally without a new dashboard.
    if name=='shot_disheartened':paste(im,obj,(430,514,1120,594))
    elif t-s.start<.8:
        u=ease((t-s.start)/.8);rect=lerp((430,514,1120,594),(430,380,1120,460),u)
        if u>.5:obj=Image.blend(obj,im.crop(rect).resize(obj.size),ease((u-.5)*2))
        paste(im,obj,rect)

def final_callback(im,t,s):
    name=s.fn.__name__
    if name not in {'shot_only_execution','shot_have_you_back','shot_run_again','shot_red_trapped'}:return
    i=INDEX[id(BYNAME['shot_only_execution'])];canvas,_=endpoint(i)
    if name=='shot_only_execution' and (t-s.start)/(s.end-s.start)<.65:return
    # Actual selected "execution" remains as a semantic echo of chorus1 ONLY.
    tile=canvas.crop((430,110,620,148))
    dest=(954,568,1144,598)
    if name=='shot_only_execution':
        u=ease(((t-s.start)/(s.end-s.start)-.65)/.30)
        dest=lerp((430,110,620,148),dest,u)
    paste(im,tile,dest)

def falling_words(im,t,s):
    if s.fn.__name__!='shot_whale_fall':return
    age=t-s.start
    if age>2.8:return
    # Each actual output word leaves its old grid coordinate and breaks into
    # marine-snow fragments over the unchanged FULL whale-fall canvas.
    prev=INDEX[id(BYNAME['shot_love_loop'])];canvas,_=endpoint(prev)
    srcshot=ALL[prev]
    oldgeom=stage.geometry(*layout(srcshot));newgeom=stage.geometry(*layout(s))
    layer=Image.new('RGBA',im.size);d=ImageDraw.Draw(layer)
    for row in range(10):
        for col in range(11):
            delay=.018*(row+col);a=max(0.,age-delay)
            if a>2.5:continue
            src=(600+col*50,76+row*20,646+col*50,96+row*20)
            oldpos=rect_screen(src,srcshot)
            ox,oy=oldpos[:2]
            x=ox+22*math.sin(a*1.4+col)*a;y=oy+25*a+31*a*a
            word=canvas.crop(src).convert('RGBA')
            if a<1.1:
                word=tk.scale_alpha(word,max(0.,1-a*.55))
                layer.alpha_composite(word,(round(x),round(y)))
            else:
                color=tk.blue(max(0.,.7-(a-1.1)*.42))+(180,)
                for q in range(4):
                    xx=x+q*9+math.sin(q+row+a)*8;yy=y+q*6
                    d.rectangle((xx,yy,xx+2,yy+2),fill=color)
    # All falling text/snow is clipped to the current FULL painting viewport.
    viewport=rect_screen(engine.FULL,s)
    clip=Image.new('L',im.size,0);ImageDraw.Draw(clip).rectangle(viewport,fill=255)
    layer.putalpha(ImageChops.multiply(layer.getchannel('A'),clip))
    im.paste(layer,(0,0),layer)

def departure_move(t,n,s):
    i=INDEX[id(s)];lt=t-s.start
    if s.fn.__name__!='shot_you_left' or i==0 or lt>=.32:return None
    prev=ALL[i-1]
    if prev.fn.__name__ not in {'shot_completion','shot_you_left'}:return None
    body=raw(t,n,s);canvas=body['canvas'];u=ease(lt/.32)
    ga={e['id']:e for e in stage.geometry(*layout(prev))};gb={e['id']:e for e in stage.geometry(*layout(s))}
    out=stage.background(t)
    for key in sorted(set(ga)|set(gb)):
        a=ga.get(key) or gb[key];b=gb.get(key) or ga[key]
        rect=lerp(a['dst'],b['dst'],u)
        source=b.get('src') or a.get('src')
        if source is not None:paste(out,canvas.crop(source),rect)
    body['ctx'].img=out;body['ctx'].d=ImageDraw.Draw(out)
    stage.chrome(body['ctx'],*layout(s));you_reference(out,t,s)
    return engine.post(out,None)

def base_frame(t,n,s):
    if s.fn.__name__ in CHORUS_NAMES:
        return approved.render_frame(n)
    body=raw(t,n,s);im=engine.finish(body)
    if body['black'] or body['ctx'].no_chrome:return im
    return im

def frame(n):
    t=n/FPS;s=engine.shot_at(t);name=s.fn.__name__
    if name in CHORUS_NAMES:return approved.render_frame(n)
    if name=='shot_black':return base_frame(t,n,s)
    moved=departure_move(t,n,s)
    if moved is not None:return moved
    tr=engine.transition_at(t)
    if tr:
        cut,a,b,spec,pre,post=tr;key=(a.fn.__name__,b.fn.__name__)
        if key==('shot_strange','shot_eggplant'):
            # Exact sample return: outgoing sample's black ending powers back on.
            p=(t-cut+pre)/(pre+post)
            aa=approved.render_frame(min(round(t*FPS),1764))
            bb=base_frame(max(t,b.start),max(n,math.ceil(b.start*FPS)),b)
            return transitions.apply('crt',aa,engine.post(bb,None),p,random.Random(n*31))
        if key in KEEP_TRANSITIONS:
            # Source-authored zoom/pan/spin/reassembly are kept only where tied to
            # real visible content; normal glide fallback is never invoked here.
            return engine.render_frame(t,None,n,s)
    im=base_frame(t,n,s)
    if name in {'shot_power','shot_collapse'}:return engine.post(im,None)
    local_update(im,t,s);handoff(im,t,s);you_reference(im,t,s);reward_reference(im,t,s)
    final_callback(im,t,s);falling_words(im,t,s)
    return engine.post(im,None)

def scene_map():
    rows=[]
    for i,s in enumerate(ALL):
        name=s.fn.__name__;prev=ALL[i-1].fn.__name__ if i else None
        carrier=HANDOFFS.get(name)
        if name in CHORUS_NAMES:policy='approved chorus continuity renderer';detail='sample/vector/ONLY/YOU and local/fullscreen handoffs retained'
        elif name=='shot_you_left':policy='geometry retraction with retained YOU';detail='same ping content and selected reference, no particle reflow'
        elif name=='shot_whale_fall':policy='actual output love words fall into marine snow';detail='original FULL cinema painting preserved and clipped'
        elif carrier:policy='actual object carry + local panel update';detail=carrier[2]
        elif (prev,name) in KEEP_TRANSITIONS:policy='preserved motivated '+str(direction.CHOREO.get((prev,name),{}).get('kind'));detail='original scene art and transform'
        elif name in {'shot_exec_hit','shot_count','shot_last_execution','shot_black'}:policy='original musical hard hit / ending';detail='special layouts, EPERM and207.58s cutoff preserved'
        elif name in KEEP_STAGE:policy='preserved shell/raw staging';detail='original body function and narrative treatment'
        else:policy='stable workspace / local panel update';detail='original body and scale, incidental window-layout churn removed'
        rows.append(dict(index=i,name=name,params=s.params,start=s.start,end=s.end,chapter=s.chapter,
            original_layout=ORIGINAL_LAYOUTS[id(s)],new_layout=layout(s),content='preserved original drawing; adapted staging',
            transition_policy=policy,content_carrier=detail,source_rect=carrier[0] if carrier else None,
            destination_rect=carrier[1] if carrier else None))
    assert all(s.fn.__name__!='shot_placeholder' for s in ALL)
    assert abs(ALL[0].start)<1e-9 and abs(ALL[-1].end-211)<1e-9
    assert all(abs(a.end-b.start)<1e-6 for a,b in zip(ALL,ALL[1:]))
    write_json('scene_coverage.json',rows)
    return rows

def sheet(path,times,columns=4,width=400):
    rows=math.ceil(len(times)/columns);height=round(width*720/1280)
    out=Image.new('RGB',(columns*width,rows*(height+27)),tk.BG);d=ImageDraw.Draw(out)
    for j,t in enumerate(times):
        n=round(t*FPS);im=frame(n);im.save(path.parent/f'{n:05d}.png')
        x=j%columns*width;y=j//columns*(height+27)
        out.paste(im.resize((width,height)),(x,y+25))
        d.text((x+5,y+5),f'{n/FPS:.3f}s {engine.shot_at(n/FPS).fn.__name__[5:]}',fill=(211,225,242))
    out.save(path)

def preflight():
    out=ROOT/'preflight';out.mkdir(exist_ok=True);scene_map()
    times=[1.1,5.0,7.3,11.1,14.6,19.,22.8,27.5,31.,35.,38.3,42.5,46.,48.3,52.6,
           55.8,62.5,65.7,67.3,71.65,74.,78.,82.,89.5,93.,99.,104.5,109.,112.,115.5,
           117.2,120.,124.7,128.5,133.,136.5,140.3,144.5,148.,152.,157.,160.,164.,166.7,
           169.,171.,174.,176.5,179.,182.,185.,188.,190.5,194.,199.,204.,207.7,210.]
    # Three sheets keep labels and plots reviewable without one microscopic image.
    for k in range(3):sheet(out/f'chapters_{k+1}.png',times[k*20:(k+1)*20])
    strips=[('sample_return',[73.35,73.54,73.70,73.95]),
            ('user_left',[110.4,111.2,113.2,115.8,116.5,117.3]),
            ('final_chorus',[162.2,163.4,164.2,166.,167.1,169.]),
            ('love_to_whale',[192.8,193.5,194.,194.7,195.5,196.2])]
    for label,ts in strips:sheet(out/(label+'.png'),ts,columns=len(ts),width=400)
    write_json('preflight.json',dict(times=times,boundaries={k:v for k,v in strips},scene_count=len(ALL)))
    print('PREFLIGHT READY '+str(out),flush=True)

def worker(k,first,last):
    """One bounded CPU renderer + one single-thread encoder. No process pool forks."""
    out=ROOT/'segments';out.mkdir(exist_ok=True)
    target=out/f'segment_{k:02d}.mp4';log=out/f'worker_{k:02d}_ffmpeg.log'
    cmd=['ffmpeg','-v','error','-y','-f','rawvideo','-pix_fmt','rgb24','-s','1280x720','-r','24','-i','pipe:0',
         '-an','-c:v','libx264','-threads','1','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(target)]
    record=dict(worker_pid=os.getpid(),worker=k,first=first,last=last,frames=0,state='RUNNING',command=cmd,cwd=str(ROOT))
    with log.open('wb') as fp:
        p=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=fp,stderr=fp)
        record['encoder_pid']=p.pid;write_json(f'segments/worker_{k:02d}.json',record)
        try:
            for n in range(first,last):
                p.stdin.write(frame(n).tobytes());record['frames']=n-first+1
                if (n-first)%120==0:
                    record['last_song_time']=n/FPS;record['chapter']=engine.shot_at(n/FPS).chapter
                    write_json(f'segments/worker_{k:02d}.json',record)
                    print(f'worker{k}: {n-first}/{last-first} / song {n/FPS:.1f}s / {record["chapter"]}',flush=True)
            p.stdin.close();assert p.wait(timeout=120)==0
            record['state']='COMPLETED'
        except BaseException:
            record['state']='FAILED';record['error']=traceback.format_exc();raise
        finally:
            if p.poll() is None:p.kill();p.wait()
            record['encoder_returncode']=p.returncode;write_json(f'segments/worker_{k:02d}.json',record)
    write_json(f'segments/dance_mapping_{k:02d}.json',sb.CALLS)

PROCESSES=[]
def run(cmd,label,timeout=240):
    with (ROOT/(label+'.log')).open('wb') as log:
        p=subprocess.Popen(cmd,stdout=log,stderr=log);row=dict(label=label,pid=p.pid,command=cmd,cwd=str(ROOT),returncode=None)
        PROCESSES.append(row);write_json('processes.json',PROCESSES)
        try:rc=p.wait(timeout=timeout)
        finally:
            if p.poll() is None:p.kill();p.wait()
            row['returncode']=p.returncode;write_json('processes.json',PROCESSES)
        assert rc==0,label

def render():
    scene_map();out=ROOT/'segments';out.mkdir(exist_ok=True)
    # Balanced contiguous ranges; renderer is stateless so boundaries are exact.
    bounds=[0,1266,2532,3798,5064];active=[];logs=[]
    try:
        for k,(a,b) in enumerate(zip(bounds,bounds[1:])):
            cmd=[sys.executable,'-B','-X','utf8',str(Path(__file__).resolve()),'--worker',str(k),str(a),str(b)]
            log=(out/f'worker_{k:02d}.log').open('wb');logs.append(log)
            p=subprocess.Popen(cmd,stdout=log,stderr=log,cwd=str(ROOT));active.append((p,k))
            PROCESSES.append(dict(label=f'render_worker_{k}',pid=p.pid,command=cmd,cwd=str(ROOT),returncode=None))
            write_json('processes.json',PROCESSES)
        while any(p.poll() is None for p,k in active):
            time.sleep(3)
            for p,k in active:
                if p.poll() not in (None,0):raise RuntimeError(f'render worker{k} failed: {p.returncode}')
            if int(time.monotonic())%18<3:
                statuses=[]
                for p,k in active:
                    path=out/f'worker_{k:02d}.json'
                    if path.exists():
                        try:r=json.loads(path.read_text());statuses.append(f'{k}:{r["frames"]}/{r["last"]-r["first"]}')
                        except json.JSONDecodeError:pass
                print('render '+', '.join(statuses),flush=True)
    finally:
        for p,k in active:
            if p.poll() is None:
                # Ctrl-break is not assumed. Stop our encoder first to release worker pipe.
                state=out/f'worker_{k:02d}.json'
                if state.exists():
                    try:
                        r=json.loads(state.read_text());subprocess.run(['taskkill','/PID',str(r['encoder_pid']),'/T','/F'],capture_output=True)
                    except (KeyError,json.JSONDecodeError):pass
                p.terminate();p.wait(timeout=30)
            PROCESSES[k]['returncode']=p.returncode
        for log in logs:log.close()
        write_json('processes.json',PROCESSES)
    assert all(p.returncode==0 for p,k in active)
    lst=out/'concat.txt';lst.write_text(''.join(f"file 'segment_{k:02d}.mp4'\n" for k in range(4)),encoding='utf8')
    run(['ffmpeg','-v','error','-y','-f','concat','-safe','0','-i',str(lst),'-i',str(engine.AUDIO),
         '-map','0:v','-map','1:a','-c:v','copy','-c:a','aac','-b:a','192k','-t','211',
         '-movflags','+faststart',str(ROOT/VIDEO)],'mux')

def verify():
    run(['ffprobe','-v','error','-show_streams','-show_format','-of','json',str(ROOT/VIDEO)],'ffprobe')
    meta=json.loads((ROOT/'ffprobe.log').read_text());write_json('metadata.json',meta)
    v=next(s for s in meta['streams'] if s['codec_type']=='video');a=next(s for s in meta['streams'] if s['codec_type']=='audio')
    assert (v['width'],v['height'],v['r_frame_rate'],int(v['nb_frames']))==(1280,720,'24/1',5064)
    assert abs(float(v['duration'])-211)<.002 and abs(float(a['duration'])-211)<.03
    run(['ffmpeg','-v','error','-xerror','-i',str(ROOT/VIDEO),'-map','0:v','-map','0:a','-f','null','-'],'full_decode',300)
    original=json.loads((ROOT/'input_hashes.json').read_text());current=snapshot()
    changed=[p for p,h in original.items() if current.get(p)!=h];assert not changed,changed
    coverage=scene_map();assert len(coverage)==len(ALL)
    out=ROOT/'encoded_review';out.mkdir(exist_ok=True)
    times=[7.4,22.5,35.,47.5,62.5,65.7,73.7,89.5,112.,116.5,126.,136.5,150.,158.,166.8,173.,179.5,188.,194.,196.,204.,207.625,210.]
    frames=[round(t*FPS) for t in times]
    expr='+'.join(f'eq(n\\,{n})' for n in frames)
    run(['ffmpeg','-v','error','-y','-i',str(ROOT/VIDEO),'-vf','select='+expr,'-fps_mode','passthrough',str(out/'%02d.png')],'review_extract')
    sheetim=Image.new('RGB',(1600,6*252),tk.BG);d=ImageDraw.Draw(sheetim)
    for j,n in enumerate(frames):
        im=Image.open(out/f'{j+1:02d}.png');assert im.size==(1280,720)
        x=j%4*400;y=j//4*252;sheetim.paste(im.resize((400,225)),(x,y+25));d.text((x+5,y+5),f'{n/FPS:.3f}s',fill=(220,230,245))
    sheetim.save(out/'contact_sheet.png')
    # Check actual delivered frame after original hard cut is black before its late message.
    black=Image.open(out/f'{times.index(207.625)+1:02d}.png').convert('RGB')
    extrema=black.getextrema();assert max(x[1] for x in extrema)<=3,extrema
    records=[json.loads(p.read_text()) for p in (ROOT/'segments').glob('worker_??.json')]
    assert len(records)==4 and sum(r['frames'] for r in records)==5064
    assert all(r['state']=='COMPLETED' and r['encoder_returncode']==0 for r in records)
    write_json('validation.json',dict(status='PASS',video_frames=5064,duration=211.,fps=24,size=[1280,720],
        source_scene_count=len(ALL),coverage_scene_count=len(coverage),placeholder_count=0,hard_cut=207.58,
        delivered_postcut_black_extrema=extrema,protected_files=len(original),changed_inputs=changed,
        full_audio_video_decode=True,visual_acceptance='director preview; parent/user full-song review pending'))
    write_json('output_manifest.json',dict(video=VIDEO,sha256=sha(ROOT/VIDEO),bytes=(ROOT/VIDEO).stat().st_size,
        comparison='index.html',baseline='../full/tui_pv_full_deepsea_anchor.mp4',frames=5064,duration=211.,
        approved_chorus_source='continuity_chorus_v1/continuity.py',fresh_external_assets_used=False))
    print('FINAL CHECKS PASS',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--preflight',action='store_true');ap.add_argument('--render',action='store_true');ap.add_argument('--verify',action='store_true');ap.add_argument('--worker',nargs=3,type=int)
    args=ap.parse_args()
    if args.worker:worker(*args.worker)
    else:
        if not (ROOT/'input_hashes.json').exists():write_json('input_hashes.json',snapshot())
        if args.preflight:preflight()
        if args.render:render()
        if args.verify:verify()
