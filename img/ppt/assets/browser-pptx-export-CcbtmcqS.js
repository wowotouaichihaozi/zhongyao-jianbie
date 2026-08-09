import{zipSync as C,strToU8 as b}from"./browser-_Ncw3Jhn.js";const u=12192e3,g=6858e3,f=1600,x=900,T=a=>a.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");function w(a){const n=new DOMParser().parseFromString(a,"text/html"),s=[],t=n.querySelectorAll("h1, h2, h3, h4, p, li, td, th, strong, span");let o=6e5;for(const c of t){const d=c.textContent?.trim();if(!d||d.length<2)continue;const p=c.tagName.toLowerCase();let e=24,r=!1,i="333333";p==="h1"?(e=48,r=!0,i="111827"):p==="h2"?(e=32,r=!0,i="1F2937"):p==="h3"?(e=24,r=!0,i="374151"):p==="h4"?(e=20,r=!0,i="4B5563"):p==="p"?(e=18,i="44506A"):p==="li"?(e=16,i="44506A"):p==="td"||p==="th"?(e=14,i="374151"):p==="strong"&&(r=!0);const m=d.length>200?`${d.substring(0,197)}...`:d,h=Math.floor(1e7/(e*12700)),F=Math.ceil(m.length/Math.max(h,10)),v=Math.round(e*12700*1.4),S=Math.max(v*F,v);if(s.push({text:m,fontSize:e,bold:r,color:i,top:o,left:6e5,width:11e6,height:S}),o+=S+1e5,o>g-4e5)break}if(s.length===0){const c=a.match(/<title[^>]*>([^<]+)<\/title>/i),d=c?c[1].trim():"Slide";s.push({text:d,fontSize:40,bold:!0,color:"111827",top:25e5,left:1e6,width:1e7,height:15e5})}return s}function $(a,l){const n=Array.from({length:a},(s,t)=>`  <Override PartName="/ppt/slides/slide${t+1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`).join(`
`);return`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  ${l?'<Default Extension="png" ContentType="image/png"/>':""}
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>
  <Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>
  <Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>
${n}
</Types>`}const L=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>`;function M(a){return`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rIdSm"/></p:sldMasterIdLst>
  <p:sldIdLst>
${Array.from({length:a},(n,s)=>`    <p:sldId id="${256+s}" r:id="rId${s+1}"/>`).join(`
`)}
  </p:sldIdLst>
  <p:sldSz cx="${u}" cy="${g}" type="wide"/>
  <p:notesSz cx="${g}" cy="${u}"/>
</p:presentation>`}function I(a){return`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdSm" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>
${Array.from({length:a},(n,s)=>`  <Relationship Id="rId${s+1}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${s+1}.xml"/>`).join(`
`)}
</Relationships>`}const y='<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>',R=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldMaster xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>${y}</p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldMaster>`,E=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>
</Relationships>`,D=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sldLayout xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" type="blank" preserve="1">
  <p:cSld><p:spTree>${y}</p:spTree></p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sldLayout>`,O=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>
</Relationships>`,A=`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<a:theme xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" name="OhMyPPT">
  <a:themeElements>
    <a:clrScheme name="OhMyPPT"><a:dk1><a:srgbClr val="111827"/></a:dk1><a:lt1><a:srgbClr val="FFFFFF"/></a:lt1><a:dk2><a:srgbClr val="1F2937"/></a:dk2><a:lt2><a:srgbClr val="F3F4F6"/></a:lt2><a:accent1><a:srgbClr val="2563EB"/></a:accent1><a:accent2><a:srgbClr val="7C3AED"/></a:accent2><a:accent3><a:srgbClr val="06B6D4"/></a:accent3><a:accent4><a:srgbClr val="10B981"/></a:accent4><a:accent5><a:srgbClr val="F59E0B"/></a:accent5><a:accent6><a:srgbClr val="EF4444"/></a:accent6><a:hlink><a:srgbClr val="2563EB"/></a:hlink><a:folHlink><a:srgbClr val="7C3AED"/></a:folHlink></a:clrScheme>
    <a:fontScheme name="OhMyPPT"><a:majorFont><a:latin typeface="Aptos Display"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface=""/></a:majorFont><a:minorFont><a:latin typeface="Aptos"/><a:ea typeface="Microsoft YaHei"/><a:cs typeface=""/></a:minorFont></a:fontScheme>
    <a:fmtScheme name="Office"><a:fillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:fillStyleLst><a:lnStyleLst><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln><a:ln w="6350"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:ln></a:lnStyleLst><a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst><a:bgFillStyleLst><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:solidFill><a:schemeClr val="phClr"/></a:solidFill></a:bgFillStyleLst></a:fmtScheme>
  </a:themeElements>
</a:theme>`;function P(a,l){return`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rIdLayout" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>
  ${a?`<Relationship Id="rIdImage" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="../media/${l}"/>`:""}
</Relationships>`}function U(){return`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      ${y}
      <p:pic>
        <p:nvPicPr><p:cNvPr id="2" name="Slide image"/><p:cNvPicPr/><p:nvPr/></p:nvPicPr>
        <p:blipFill><a:blip r:embed="rIdImage"/><a:stretch><a:fillRect/></a:stretch></p:blipFill>
        <p:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="${u}" cy="${g}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></p:spPr>
      </p:pic>
    </p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
  <p:transition spd="med" advClick="1"><p:fade/></p:transition>
</p:sld>`}function _(a,l){let n=3;const s=l.map(o=>{const c=n++,d=o.text.split(`
`).map(p=>`<a:p><a:pPr/><a:r><a:rPr lang="zh-CN" sz="${Math.round(o.fontSize*100)}"${o.bold?' b="1"':""} dirty="0"><a:solidFill><a:srgbClr val="${o.color}"/></a:solidFill><a:latin typeface="Aptos"/><a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>${T(p)}</a:t></a:r></a:p>`).join("");return`<p:sp><p:nvSpPr><p:cNvPr id="${c}" name="Text ${c}"/><p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="${o.left}" y="${o.top}"/><a:ext cx="${o.width}" cy="${o.height}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t"/><a:lstStyle/>${d}</p:txBody></p:sp>`}).join(`
      `),t=`<p:sp><p:nvSpPr><p:cNvPr id="2" name="Title 2"/><p:cNvSpPr/><p:nvPr/></p:nvSpPr><p:spPr><a:xfrm><a:off x="600000" y="300000"/><a:ext cx="11000000" cy="800000"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr><p:txBody><a:bodyPr wrap="square" lIns="0" tIns="0" rIns="0" bIns="0" anchor="t"/><a:lstStyle/><a:p><a:pPr/><a:r><a:rPr lang="zh-CN" sz="3600" b="1" dirty="0"><a:solidFill><a:srgbClr val="111827"/></a:solidFill><a:latin typeface="Aptos Display"/><a:ea typeface="Microsoft YaHei"/></a:rPr><a:t>${T(a)}</a:t></a:r></a:p></p:txBody></p:sp>`;return`<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:bg><p:bgPr><a:solidFill><a:srgbClr val="F5F1E8"/></a:solidFill><a:effectLst/></p:bgPr></p:bg>
    <p:spTree>${y}${t}${s}</p:spTree>
  </p:cSld>
  <p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>
</p:sld>`}function N(a){const l=a.match(/^data:image\/png;base64,(.+)$/);if(!l)return null;const n=atob(l[1]),s=new Uint8Array(n.length);for(let t=0;t<n.length;t++)s[t]=n.charCodeAt(t);return s}const H=a=>new Promise(l=>setTimeout(l,a));async function k(a){const l=document.createElement("iframe");l.style.cssText=`position:fixed;left:-10000px;top:0;width:${f}px;height:${x}px;border:0;pointer-events:none;opacity:0;`,l.setAttribute("aria-hidden","true"),document.body.appendChild(l);try{l.srcdoc=a,await new Promise(m=>{l.onload=()=>m(),setTimeout(m,1200)});const n=l.contentDocument;if(!n?.documentElement||!n.body)throw new Error("Preview document was not available");const s=n.createElement("style");s.textContent=`
      html, body { width: ${f}px !important; height: ${x}px !important; margin: 0 !important; overflow: hidden !important; }
      [data-anim] { opacity: 1 !important; transform: none !important; filter: none !important; visibility: visible !important; }
      *, *::before, *::after { animation: none !important; transition: none !important; }
    `,n.head.appendChild(s),await n.fonts?.ready?.catch(()=>{}),await Promise.all(Array.from(n.images).map(m=>m.complete?Promise.resolve():new Promise(h=>{m.onload=()=>h(),m.onerror=()=>h(),setTimeout(h,1e3)}))),await H(100);const t=Array.from(n.querySelectorAll("style")).map(m=>m.outerHTML).join(`
`),o=n.body.innerHTML,c=`<div xmlns="http://www.w3.org/1999/xhtml" style="width:${f}px;height:${x}px;overflow:hidden;background:white;">${t}${o}</div>`,d=`<svg xmlns="http://www.w3.org/2000/svg" width="${f}" height="${x}" viewBox="0 0 ${f} ${x}"><foreignObject width="100%" height="100%">${c}</foreignObject></svg>`,p=`data:image/svg+xml;charset=utf-8,${encodeURIComponent(d)}`,e=new Image;e.decoding="async",e.src=p,await e.decode();const r=document.createElement("canvas");r.width=f,r.height=x;const i=r.getContext("2d");if(!i)throw new Error("Canvas context was not available");return i.fillStyle="#ffffff",i.fillRect(0,0,f,x),i.drawImage(e,0,0,f,x),r.toDataURL("image/png")}finally{l.remove()}}async function j(a,l,n){if(!a.length)throw new Error("No pages to export");const s={},t=(e,r)=>{s[e]=b(r)},o=a.length;let c=!1;t("_rels/.rels",L),t("ppt/presentation.xml",M(o)),t("ppt/_rels/presentation.xml.rels",I(o)),t("ppt/slideMasters/slideMaster1.xml",R),t("ppt/slideMasters/_rels/slideMaster1.xml.rels",E),t("ppt/slideLayouts/slideLayout1.xml",D),t("ppt/slideLayouts/_rels/slideLayout1.xml.rels",O),t("ppt/theme/theme1.xml",A);for(let e=0;e<o;e++){n?.(e+1,o);const r=a[e],i=`slide${e+1}.png`;try{const m=await k(r.html),h=N(m);if(!h)throw new Error("PNG conversion failed");c=!0,s[`ppt/media/${i}`]=h,t(`ppt/slides/slide${e+1}.xml`,U()),t(`ppt/slides/_rels/slide${e+1}.xml.rels`,P(!0,i))}catch{const m=w(r.html);t(`ppt/slides/slide${e+1}.xml`,_(r.title,m)),t(`ppt/slides/_rels/slide${e+1}.xml.rels`,P(!1,i))}}t("[Content_Types].xml",$(o,c));const d=C(s,{level:6}),p=new Blob([d],{type:"application/vnd.openxmlformats-officedocument.presentationml.presentation"});return URL.createObjectURL(p)}export{j as exportToPptx,k as renderHtmlToPng};
