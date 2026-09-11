"""Render a narrated project video from a reviewed storyboard and real screenshots."""
import json,subprocess,sys,textwrap
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps

story_path=Path(sys.argv[1]).resolve()
base=story_path.parent
story=json.loads(story_path.read_text())
build=base/'.render';build.mkdir(exist_ok=True)
font_path='/System/Library/Fonts/Supplemental/Arial.ttf'
bold_path='/System/Library/Fonts/Supplemental/Arial Bold.ttf'
font=lambda size,bold=False:ImageFont.truetype(bold_path if bold else font_path,size)
segments=[];captions=[];offset=0

def stamp(seconds):
 ms=round(seconds*1000); h,ms=divmod(ms,3600000);m,ms=divmod(ms,60000);s,ms=divmod(ms,1000)
 return f'{h:02}:{m:02}:{s:02},{ms:03}'

for index,scene in enumerate(story['scenes'],1):
 canvas=Image.new('RGB',(1920,1080),'#102128');d=ImageDraw.Draw(canvas)
 d.rectangle((0,0,1920,12),fill=story['accent'])
 d.text((72,52),story['project'].upper(),font=font(30,True),fill=story['accent'])
 d.text((1845,52),f'{index:02} / {len(story["scenes"]):02}',font=font(28),fill='#D6E5E8',anchor='ra')
 title=textwrap.wrap(scene['title'],width=55)
 for line_n,line in enumerate(title):d.text((72,111+line_n*62),line,font=font(51,True),fill='#FFFFFF')
 if scene.get('image'):
  screenshot=Image.open(base/scene['image']).convert('RGB')
  screenshot=ImageOps.contain(screenshot,(1776,755),Image.Resampling.LANCZOS)
  canvas.paste(screenshot,((1920-screenshot.width)//2,240+(755-screenshot.height)//2))
 else:
  for n,point in enumerate(scene.get('points',[])):
   y=290+n*205
   d.rounded_rectangle((72,y,1848,y+170),radius=22,fill='#1C3840')
   d.ellipse((107,y+48,181,y+122),fill=story['accent'])
   d.text((144,y+85),str(n+1),font=font(35,True),fill='#102128',anchor='mm')
   for l,text in enumerate(textwrap.wrap(point,width=53)):
    d.text((225,y+50+l*52),text,font=font(43,True),fill='#F5F5E9')
 d.text((72,1035),'FICTIONAL DEMO  |  Screenshots from the working prototype  |  Synthetic narration',font=font(22),fill='#B5CDD0')
 png=build/f'{index:02}.png';canvas.save(png)
 narration=build/f'{index:02}.txt';narration.write_text(scene['narration'])
 audio=build/f'{index:02}.aiff'
 subprocess.run(['say','-v',story.get('voice','Samantha'),'-r',str(story.get('rate',155)),'-f',str(narration),'-o',str(audio)],check=True)
 duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',str(audio)]))
 video=build/f'{index:02}.mp4'
 subprocess.run(['ffmpeg','-y','-loglevel','error','-loop','1','-framerate','12','-i',str(png),'-i',str(audio),'-c:v','libx264','-preset','veryfast','-crf','23','-t',str(duration+1),'-vf','format=yuv420p','-af','apad=pad_dur=1','-c:a','aac','-b:a','128k','-movflags','+faststart',str(video)],check=True)
 segments.append(video)
 words=scene['narration'].split();chunks=[words[n:n+13] for n in range(0,len(words),13)];used=0
 for chunk in chunks:
  start=offset+duration*used/len(words);used+=len(chunk);end=offset+duration*used/len(words)
  captions.append(f'{len(captions)+1}\n{stamp(start)} --> {stamp(end)}\n'+ ' '.join(chunk)+'\n')
 offset+=duration+1
 print(f'Scene {index}: {duration:.1f}s',flush=True)
concat=build/'concat.txt';concat.write_text(''.join(f"file '{p.as_posix()}'\n" for p in segments))
output=base/(story['project'].lower().replace(' ','-')+'-demo.mp4')
subprocess.run(['ffmpeg','-y','-loglevel','error','-f','concat','-safe','0','-i',str(concat),'-c','copy','-movflags','+faststart',str(output)],check=True)
(base/'captions.srt').write_text('\n'.join(captions))
(base/'NARRATION.md').write_text('# Demo narration\n\n'+'\n\n'.join(scene['narration'] for scene in story['scenes'])+'\n')
print(json.dumps({'video':str(output),'duration_seconds':round(offset,2),'scenes':len(segments)}),flush=True)
