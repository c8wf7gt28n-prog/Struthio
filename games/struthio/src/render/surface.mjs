// STRUTHIO ARCADE · tiny RGBA surface helpers (fill, rect, circle) used to paint the atlas.
function surface(w,h,rgba=[0,0,0,0]){
const p=new Uint8Array(w*h*4);
for (let i=0;i<w*h;i++) p.set(rgba,i*4);
return{w,h,p};
}
function color(hex,a=255){
const s=hex.replace('#','');
return[parseInt(s.slice(0,2),16),parseInt(s.slice(2,4),16),parseInt(s.slice(4,6),16),a];
}
function pixel(s,x,y,c){
x=Math.floor(x);y=Math.floor(y);
if (x<0||y<0||x>=s.w||y>=s.h) return;
s.p.set(c,(y*s.w+x)*4);
}
function rect(s,x,y,w,h,c){
for (let yy=Math.max(0,y);yy<Math.min(s.h,y+h);yy++) for (let xx=Math.max(0,x);xx<Math.min(s.w,x+w);xx++) pixel(s,xx,yy,c);
}
function circle(s,cx,cy,r,c,thick=1){
const r2=r*r,inner=(r-thick)*(r-thick);
for (let y=-r;y<=r;y++) for (let x=-r;x<=r;x++){const d=x*x+y*y;if (d<=r2&&d>=inner) pixel(s,cx+x,cy+y,c);}
}
export{surface,color,rect,circle};
