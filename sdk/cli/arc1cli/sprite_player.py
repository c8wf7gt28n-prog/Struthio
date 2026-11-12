"""Small elapsed-time sprite state machine. No UI, assets, files or tool authority."""
import time


class SpritePlayer:
    def __init__(self, clips, clock=time.monotonic):
        if not isinstance(clips,dict) or not 1<=len(clips)<=64:raise ValueError('Invalid sprite clips')
        self.clips={}
        for name,clip in clips.items():
            frames=clip.get('frames');duration=clip.get('frame_ms')
            if not isinstance(name,str) or not isinstance(frames,list) or not 1<=len(frames)<=64:
                raise ValueError('Invalid sprite frame list')
            if any(type(i) is not int or not 0<=i<256 for i in frames):raise ValueError('Invalid sprite frame index')
            if type(duration) is not int or not 20<=duration<=5000:raise ValueError('Invalid sprite timing')
            if type(clip.get('loop')) is not bool or type(clip.get('mirror',False)) is not bool:raise ValueError('Invalid sprite flags')
            self.clips[name]={'frames':tuple(frames),'frame_ms':duration,'loop':clip['loop'],'mirror':clip.get('mirror',False)}
        self.clock=clock;self.state=None;self.started=0.

    def select(self,name,now=None,restart=False):
        if name not in self.clips:raise ValueError('Unknown sprite state: '+str(name))
        if name!=self.state or restart:
            self.state=name;self.started=self.clock() if now is None else float(now)

    def frame(self,name=None,now=None,reduced=False):
        moment=self.clock() if now is None else float(now)
        self.select(name or self.state or 'idle',moment)
        clip=self.clips[self.state]
        step=0 if reduced else int(max(0.,moment-self.started)*1000/clip['frame_ms'])
        count=len(clip['frames']);done=not clip['loop'] and step>=count
        index=step%count if clip['loop'] else min(step,count-1)
        return {'state':self.state,'frame':clip['frames'][index],'mirror':clip['mirror'],
                'finished':done,'frame_ms':clip['frame_ms'],'loop':clip['loop']}
