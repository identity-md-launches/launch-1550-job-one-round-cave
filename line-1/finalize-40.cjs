// Retain only generated earth pigment on vacant rock; never redraw ancestors.
const fs = require('node:fs');
const zlib = require('node:zlib');
const crypto = require('node:crypto');
const digest = b => crypto.createHash('sha256').update(b).digest('hex');
const wallPath = 'artifacts/line-1/wall.png';
const outputPath = 'artifacts/line-1/wall-v21.png';
const original = fs.readFileSync(wallPath), generated = fs.readFileSync(outputPath);
const previous = JSON.parse(fs.readFileSync('dist/line-1/39.json'));
if (digest(original) !== previous.image.split('/').pop()) throw Error('wrong ancestor');
if (fs.existsSync('dist/line-1/40.json')) throw Error('record already exists');
function crc32(bytes) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let i=0;i<8;i++) crc = (crc>>>1) ^ ((crc&1) ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}
function decode(raw) {
  if (!raw.subarray(0,8).equals(Buffer.from('89504e470d0a1a0a','hex'))) throw Error('not PNG');
  let width, height, channels, compressed=[];
  for (let p=8;p<raw.length;) {
    const n=raw.readUInt32BE(p), tag=raw.toString('ascii',p+4,p+8), body=raw.subarray(p+8,p+8+n);
    if(crc32(raw.subarray(p+4,p+8+n)) !== raw.readUInt32BE(p+8+n)) throw Error('PNG CRC');
    if(tag==='IHDR') {
      width=body.readUInt32BE(0); height=body.readUInt32BE(4);
      if(body[8]!==8 || ![2,6].includes(body[9]) || body[10] || body[11] || body[12]) throw Error('PNG layout');
      channels=body[9]===2?3:4;
    } else if(tag==='IDAT') compressed.push(body);
    else if(tag==='IEND') break;
    p+=12+n;
  }
  const stride=width*channels, data=zlib.inflateSync(Buffer.concat(compressed));
  if(data.length!==(stride+1)*height) throw Error('PNG data length');
  const pixels=Buffer.alloc(width*height*channels);
  for(let y=0;y<height;y++) {
    const mode=data[y*(stride+1)];
    for(let x=0;x<stride;x++) {
      const at=y*stride+x, a=x>=channels?pixels[at-channels]:0;
      const b=y?pixels[at-stride]:0, c=y&&x>=channels?pixels[at-stride-channels]:0;
      let predicted;
      if(mode===0) predicted=0;
      else if(mode===1) predicted=a;
      else if(mode===2) predicted=b;
      else if(mode===3) predicted=(a+b)>>1;
      else if(mode===4) {
        const p=a+b-c, da=Math.abs(p-a), db=Math.abs(p-b), dc=Math.abs(p-c);
        predicted=da<=db&&da<=dc?a:(db<=dc?b:c);
      } else throw Error('PNG filter');
      pixels[at]=(data[y*(stride+1)+1+x]+predicted)&255;
    }
  }
  return {width,height,channels,pixels};
}
function encode(width,height,pixels) {
  function chunk(tag,body) {
    const name=Buffer.from(tag), n=Buffer.alloc(4), crc=Buffer.alloc(4);
    n.writeUInt32BE(body.length); crc.writeUInt32BE(crc32(Buffer.concat([name,body])));
    return Buffer.concat([n,name,body,crc]);
  }
  const header=Buffer.alloc(13); header.writeUInt32BE(width); header.writeUInt32BE(height,4);
  header[8]=8; header[9]=2;
  const rows=[];
  for(let y=0;y<height;y++) rows.push(Buffer.from([0]),pixels.subarray(y*width*3,(y+1)*width*3));
  return Buffer.concat([Buffer.from('89504e470d0a1a0a','hex'),chunk('IHDR',header),
    chunk('IDAT',zlib.deflateSync(Buffer.concat(rows))),chunk('IEND',Buffer.alloc(0))]);
}
const old=decode(original), insert=decode(generated);
if(old.width!==1254||old.height!==1254||old.channels!==3) throw Error('cave dimensions');
function pigment(x,y) {
  const i=(y*insert.width+x)*insert.channels;
  const [r,g,b]=insert.pixels.subarray(i,i+3), alpha=insert.channels===4?insert.pixels[i+3]:255;
  const red=r>65&&r>g*1.3&&r>b*1.55, dark=Math.max(r,g,b)<125;
  return alpha>=165&&(red||dark)?{alpha,tone:red?[151,61,31]:[40,29,21]}:null;
}
let x0=insert.width,y0=insert.height,x1=0,y1=0;
for(let y=0;y<insert.height;y++) for(let x=0;x<insert.width;x++) if(pigment(x,y)) {
  x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y);
}
const left=1050, top=270, pw=76, ph=116, pixels=Buffer.from(old.pixels);
let changed=0;
for(let y=0;y<ph;y++) for(let x=0;x<pw;x++) {
  const p=pigment(x0+Math.floor(x*(x1-x0+1)/pw),y0+Math.floor(y*(y1-y0+1)/ph));
  if(!p) continue;
  const at=((top+y)*old.width+left+x)*3, strength=.72*p.alpha/255;
  for(let c=0;c<3;c++) pixels[at+c]=Math.round(old.pixels[at+c]*(1-strength)+p.tone[c]*strength);
  if(!pixels.subarray(at,at+3).equals(old.pixels.subarray(at,at+3))) changed++;
}
let outside=0, total=0;
for(let y=0;y<old.height;y++) for(let x=0;x<old.width;x++) {
  const at=(y*old.width+x)*3;
  if(!pixels.subarray(at,at+3).equals(old.pixels.subarray(at,at+3))) {
    total++;
    if(!(x>=left&&x<left+pw&&y>=top&&y<top+ph)) outside++;
  }
}
if(changed<250 || total!==changed || outside) throw Error('preservation check failed');
const final=encode(old.width,old.height,pixels);
if(!decode(final).pixels.equals(pixels)) throw Error('PNG round trip failed');
fs.writeFileSync(outputPath,final); fs.writeFileSync(wallPath,final);
const record={name:'The Flint and Its Impression',image:'https://api.imd.fun/artifacts/'+digest(final),
  attributes:[['Cave','Base'],['Wall','Line 1'],['Number',40],['Left behind','code-proof-check'],
    ['Meaning','An ochre flint fits the charcoal impression that remembers its shape.'],
    ['One thing','portable live Ethereum state snapshots']].map(([trait_type,value])=>({trait_type,value}))};
fs.writeFileSync('dist/line-1/40.json',JSON.stringify(record,null,2)+'\n');
const review={source_record:39,record_number:40,source_sha256:digest(original),
  generated_sha256:digest(generated),wall_sha256:digest(final),png_dimensions:[old.width,old.height],
  png_format:'8-bit RGB PNG',png_bytes:final.length,addition_rectangle:[left,top,pw,ph],
  changed_pixels:changed,changed_pixels_outside_rectangle:outside,new_hands_or_stencils:0,
  visual_review:'Pending final PNG and JPEG inspection.',
  unmet_visual_requirements:['Inherited rock looks photographic; it was preserved to retain the cave.']};
fs.writeFileSync('line-1/wall-review-40.json',JSON.stringify(review,null,2)+'\n');
console.log(JSON.stringify(review,null,2));
