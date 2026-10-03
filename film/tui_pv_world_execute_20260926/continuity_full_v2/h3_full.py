"""H3-only character playback for every production route.

All geometry comes from continuous H3 frames, including portraits, copies and
convolution inputs. Expression names remain scene metadata. No rig, Grok or
static expression image is a runtime fallback. Historical renderers stay intact
on disk; adapters are installed only for V2_HER=h3.
"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache, wraps
import json
from pathlib import Path
import sys
import types

from PIL import Image, ImageDraw
import dancer
import rig

ROOT=Path(__file__).resolve().parent
CACHE=ROOT/'cache/h3_full_v1'
FPS=24
CLOCK=ContextVar('h3_song_time',default=None)
CALLS=[]
INSTALLED=False
ROUTES=[]

# Every interval is [start,end). Source seconds are trimmed, never pose-deduped.
# Dance cycles replay forward; the closing descent uses a separate quiet take.
PLAN=[
 (0,10,'inspect',.1,5.05,'once'),
 (10,16.082,'step',.2,7.7,'loop'),
 (16.082,29.236,'groove',.2,7.7,'loop'),
 (29.236,30.851,'present',.35,1.8,'once'),
 (30.851,33.292,'open',.3,3.2,'once'),
 (33.292,36.851,'turn',.7,5.125,'once'),
 (36.851,38.236,'open',2.1,4.7,'once'),
 (38.236,40.313,'bow',.4,4.9,'once'),
 (40.313,41.928,'open',.4,3.5,'once'),
 (41.928,44.005,'fold',.4,2.4,'once'),
 (44.005,47.236,'sweep',.3,5,'once'),
 (47.236,49.082,'inspect',1.6,4,'once'),
 (49.082,54.159,'step',.2,7.7,'loop'),
 (54.159,56.697,'open',.2,3.8,'once'),
 (56.697,58.543,'bow',.5,4.5,'once'),
 (58.543,66.159,'groove',.2,7.7,'loop'),
 (66.159,68.005,'cup',.5,3.2,'once'),
 (68.005,70.082,'step',.2,7.7,'loop'),
 (70.082,73.543,'tense',.3,3.7,'once'),
 (73.543,78.851,'present',.1,5.125,'once'),
 (78.851,80.928,'cup',.3,2.8,'once'),
 (80.928,84.62,'sway',.4,4.7,'once'),
 (84.62,88.313,'fold',.1,5.125,'once'),
 (88.313,95.236,'groove',.2,7.7,'loop'),
 (95.236,98.928,'fold',.1,5.125,'once'),
 (98.928,103.082,'sway',.2,5,'once'),
 (103.082,106.774,'open',.1,5,'once'),
 (106.774,110.416,'step',.2,7.7,'loop'),
 (110.416,115.543,'reach',0,5.125,'once'),
 (115.543,119.697,'tense',.1,4.8,'once'),
 (119.697,121.774,'sweep',.5,4.8,'once'),
 (121.774,125.236,'tense',.1,4.8,'once'),
 (125.236,128.466,'fold',.1,5.125,'once'),
 (128.466,134.466,'cup',.1,5.125,'once'),
 (134.466,138.159,'tense',.1,4.8,'once'),
 (138.159,141.389,'bow',.1,5.125,'once'),
 (141.389,147.62,'groove',.2,7.7,'loop'),
 (147.62,162.159,'step',.2,7.7,'loop'),
 (162.159,164.125,'open',.4,3.4,'once'),
 (164.125,166.792,'downbeat',.9,3.8,'once'),
 (166.792,169.543,'groove',.2,7.7,'loop'),
 (169.543,171.851,'reach',.8,4.4,'once'),
 (171.851,173.005,'sweep',1,3.5,'once'),
 (173.005,176.928,'tense',.1,4.8,'once'),
 (176.928,180.851,'inspect',.2,5,'once'),
 (180.851,184.313,'cup',.1,4.5,'once'),
 (184.313,188.167,'present',.1,5,'once'),
 (188.167,193.543,'release',.15,5.125,'once'),
 (193.543,207.084,'settle',.1,7.8,'once'),
 (207.084,212,'settle',7.8,7.95,'once'),
]
for p,q in zip(PLAN,PLAN[1:]):assert p[1]==q[0],(p,q)

@contextmanager
def at(t):
 token=CLOCK.set(float(t))
 try:yield
 finally:CLOCK.reset(token)

def now():
 t=CLOCK.get()
 if t is None:raise RuntimeError('H3 character requested outside an explicit song-time context')
 return t

def source(t):
 t=max(0,min(211.999,float(t)))
 p=next(p for p in PLAN if p[0]<=t<p[1])
 start,end,name,a,b,mode=p
 if mode=='loop':
  period=16*60/130
  u=((t-start)%period)/period
 else:u=(t-start)/(end-start)
 sec=a+(b-a)*u
 # Preserve the word-aligned accents from the accepted short sample.
 knots={'turn':[(33.292,.7),(33.75,1.2),(34.333,2),(34.8,2.7),(35.125,3.7),(36.333,4.9),(36.851,5.125)],
        'reach':[(110.416,0),(111.844,1.3),(112.25,2.9),(112.85,3.5),(114,4.5),(115.543,5.125)],
        'downbeat':[(164.125,.9),(164.8,1.25),(165.458,2.4),(166.6,3.6),(166.792,3.8)],
        'release':[(188.167,.15),(189.364,.9),(189.7,2.6),(190.4,3.7),(191.433,4.55),(193.543,5.125)]}
 if name in knots and abs(start-knots[name][0][0])<.001:
  for (x,v),(y,w) in zip(knots[name],knots[name][1:]):
   if t<y:sec=v+(w-v)*(t-x)/(y-x);break
 i=max(0,min(len(grids(name))-1,round(sec*FPS)))
 return name,i

def join(t):
 """Four-frame terminal scan, with H3 footage on both sides of every seam."""
 t=max(0,min(211.999,float(t)))
 p=next(p for p in PLAN if p[0]<=t<p[1]);boundary=p[0]
 if p[5]=='loop':boundary+=int((t-boundary)/(16*60/130))*(16*60/130)
 age=t-boundary
 if boundary>0 and age<4/FPS:
  return source(boundary-1/FPS),min(1,(age*FPS+1)/4)
 return None

def source_key(t):
 j=join(t)
 return source(t),None if j is None else (j[0],round(j[1],6))

@lru_cache(None)
def grids(name):
 data=json.loads((CACHE/f'{name}.json').read_text())
 assert len(data) in (124,192)
 return [rig.Frame(x['art'],x['shade'],x['part']) for x in data]

def frame_at(t,cols=70,rows=45):
 name,i=source(t);CALLS.append((round(t,6),name,i,'grid'))
 fr=grids(name)[i]
 j=join(t)
 if j:
  (old_name,old_i),u=j;before=grids(old_name)[old_i];cut=round(45*u)
  CALLS.append((round(t,6),old_name,old_i,'grid:join'))
  fr=rig.Frame(*(a[:cut]+b[cut:] for a,b in zip((fr.art,fr.shade,fr.part),(before.art,before.shade,before.part))))
 if (cols,rows)==(70,45):return fr
 # This route is used by the small character director; scale the rendered grid
 # there instead of cropping off her head at a smaller terminal size.
 from h3_motion import place
 return place(fr,cols,rows)

def glyph(t,width,height,tint='blue'):
 im=dancer.draw(frame_at(t),t,tint)
 scale=min(width/im.width,height/im.height,1)
 if scale<1:im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.LANCZOS)
 out=Image.new('RGBA',(width,height))
 out.alpha_composite(im,((width-im.width)//2,height-im.height))
 return out

def render(t,size,base='shy',pinned=False,tint='blue',under=.5):
 import kit
 shot=kit.sb.CURRENT
 reserve=150 if shot and shot.fn.__name__=='shot_deeply' else 0
 height=max(20,size[1]-reserve)
 return glyph(t,size[0],height,tint),None

@lru_cache(32)
def rgba(name,i):
 return Image.open(CACHE/'rgba'/name/f'{i:03}.png').convert('RGBA')

def sprite_src(expr,crop):
 t=now();name,i=source(t);CALLS.append((round(t,6),name,i,'rgba:'+crop))
 boxes={'full':(0,60,420,540),'upper':(0,70,420,350),'bust':(40,70,390,310),'face':(80,80,335,250)}
 im=rgba(name,i);j=join(t)
 if j:
  (old_name,old_i),u=j
  CALLS.append((round(t,6),old_name,old_i,'rgba:join'))
  mask=Image.new('L',im.size);ImageDraw.Draw(mask).rectangle((0,0,im.width,round(im.height*u)),fill=255)
  im=Image.composite(im,rgba(old_name,old_i),mask)
 return im.crop(boxes[crop])

def dynamic(fn):
 """Keep pure renderer caches, keyed by the actual H3 frame rather than expr."""
 raw=getattr(fn,'__wrapped__',fn)
 @lru_cache(24)
 def cached(key,args,kw):return raw(*args,**dict(kw))
 @wraps(fn)
 def wrapped(*args,**kw):return cached(source_key(now()),args,tuple(sorted(kw.items())))
 wrapped.cache_clear=cached.cache_clear
 return wrapped

def timed(fn,index):
 @wraps(fn)
 def wrapped(*args,**kw):
  t=args[index] if len(args)>index else kw['t']
  with at(t):return fn(*args,**kw)
 return wrapped

def namespaces():
 """Include importlib-loaded historical scene modules and compiled shot globals."""
 import kit
 pending=[kit,kit.v1,kit.v1.approved,kit.sb]+list(sys.modules.values())
 compiled=[kit.v1.approved.ns]
 compiled.extend(s.fn.__globals__ for s in kit.v1.ALL)
 compiled.extend(s.fn.__globals__ for s in kit.v1.approved.SHOTS.values())
 seen=set();result=[]
 for ns in compiled:
  if id(ns) not in seen:result.append(ns);seen.add(id(ns))
 while pending:
  obj=pending.pop()
  if isinstance(obj,types.ModuleType):ns=vars(obj)
  elif isinstance(obj,types.FunctionType):ns=obj.__globals__
  else:continue
  if id(ns) in seen:continue
  seen.add(id(ns))
  file=ns.get('__file__','')
  if not file or not str(Path(file).resolve()).startswith(str(ROOT.parent)):continue
  if ns is globals():continue
  result.append(ns)
  pending.extend(v for v in list(ns.values()) if isinstance(v,(types.ModuleType,types.FunctionType)))
 return result

def replace_alias(old,new,spaces):
 count=0
 for ns in spaces:
  for key,value in list(ns.items()):
   if value is old:ns[key]=new;count+=1
 ROUTES.append(dict(function=getattr(old,'__name__','?'),aliases=count))

def forbidden(*args,**kw):
 raise RuntimeError('Legacy static/Grok/rig character route reached in H3-only production')

def install():
 global INSTALLED
 if INSTALLED:return
 INSTALLED=True
 import kit,scenes,scenes_userleft,s_chorus1,scenes_exec,s_exec
 tk=kit.tk;spaces=namespaces()
 for name in ('halfblock_lum','halfblock','glyph_grid','conv_maps'):
  old=getattr(tk,name);replace_alias(old,dynamic(old),spaces)
 replace_alias(tk.sprite_src,sprite_src,spaces)
 for module,name in [(scenes_exec,'portrait_lines'),(scenes_exec,'tile_art'),(scenes_exec,'sample0_sprite'),(kit.v1.approved,'sample_object')]:
  old=getattr(module,name);replace_alias(old,dynamic(old),spaces)
 # The burst captures one outgoing H3 frame and one incoming landing frame.
 # Fix both times so independently rendered chunks cannot build different plans.
 s_exec.h3_full=sys.modules[__name__]
 kit.patch_code(s_exec.C79.plan,[
  ('cells = X.portrait_cells()', 'with h3_full.at(self.T - self.pre):\n        cells = X.portrait_cells()'),
  ('art = X.tile_art(i)\n        ax, ay = X.tile_art_xy(i)', 'with h3_full.at(self.T + 0.45):\n            art = X.tile_art(i)\n            ax, ay = X.tile_art_xy(i)'),
  ('land={k: sum(v) / len(v) for k, v in land.items()}',
   "land={k: sum(land[k]) / len(land[k]) if k in land else groups[k]['tl'] for k in range(13)}"),
 ])
 portrait= scenes_exec.portrait_lines
 burst_t=next(s.start for s in kit.v1.ALL if s.fn.__name__=='shot_execute_all')
 def burst_portrait():
  t=now()
  with at(burst_t-s_exec.C79.pre if burst_t-s_exec.C79.pre<=t<burst_t+s_exec.C79.post else t):
   return portrait()
 replace_alias(portrait,burst_portrait,spaces)
 # The embedding point cloud is a technical snapshot that must stay stable
 # while its particles converge and fly into the next shot.
 old_points=scenes.point_set
 old_points.cache_clear()
 point_time=next(s.start for s in kit.v1.ALL if s.fn.__name__=='shot_points')+.5
 @lru_cache(1)
 def point_snapshot():
  with at(point_time):return old_points()
 replace_alias(old_points,point_snapshot,spaces)
 # Clock contexts also cover old-shot sampling in cuts and particle plans.
 for module,name,index in [(kit,'her_layer',0),(kit.engine,'render_body',0),(kit.sb,'ORIGINAL_BODY',0)]:
  old=getattr(module,name);replace_alias(old,timed(old,index),spaces)
 # No synthetic body shear/hop on top of source motion in pinned overlays.
 kit.patch_code(kit._ORIGINAL_ME,[
  ('breath = int(round(1.5 * math.sin(c.t * math.pi * 2 / (BEAT * 4))))','breath = 0'),
  ('mp, off = music.react(sp, c.t, 4, 0.5 if overlay else 1.0)','mp, off = sp, 0'),
  ('hop = 4 * int(round(feat.kick ** 2 * 1.2 * (0.5 if overlay else 1.0)))','hop = 0'),
 ])
 dancer.render=render
 def small(t,expr,s,tint='blue'):
  return scenes_userleft.draw_scaled(frame_at(t),t,s,tint,None,1,0,seed=int(t*FPS))
 replace_alias(scenes_userleft.figure,small,spaces)
 def chorus_figure(shot,t,height,base=54):return glyph(t,340,height,'blue')
 replace_alias(s_chorus1.glyph_figure,chorus_figure,spaces)
 # Direct historical sidebar references have no trustworthy clock parameter.
 def sidebar_glyph(source_index,width,height,tint):return glyph(now(),width,height,tint)
 replace_alias(kit.sb.glyph,sidebar_glyph,spaces)
 def rider(t):
  with at(t):return tk.halfblock('h3','upper',70,80,2)
 scenes.RIDER[0]=rider
 compiled=kit.v1.approved.SHOTS['shot_then_i_can'].fn.__globals__
 assert compiled['halfblock'] is tk.halfblock
 assert compiled['conv_maps'] is tk.conv_maps
 # Fail closed instead of silently returning image-rig or old dance footage.
 rig.frame=forbidden
 dancer._stub_pose=forbidden
 kit.sb.ORIGINAL_RENDER=forbidden
 # Catch cached or direct expression-image reads that bypassed the adapters.
 original_open=Image.open
 @wraps(original_open)
 def guarded_open(fp,*args,**kw):
  if isinstance(fp,(str,Path)):
   p=str(fp).replace('\\','/').lower()
   if ('whale-' in p and p.endswith('.webp')) or '/sidebar_chorus_v1/source_frames/' in p:
    raise RuntimeError('Forbidden legacy character file: '+str(fp))
  return original_open(fp,*args,**kw)
 Image.open=guarded_open
