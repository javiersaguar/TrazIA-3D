// Suma gzip local de los scripts presentes en el HTML; no incluye imports diferidos ni CSS.
import { gzipSync } from "node:zlib";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
const output=resolve(process.argv[2]??"../generated/landing-weight.json");
const result=[];
for(const base of process.argv.slice(3)){
  const html=await(await fetch(new URL("/",base))).text();
  const sources=[...new Set([...html.matchAll(/<script[^>]+src="([^"]+)"/g)].map(m=>m[1]))];
  const scripts=await Promise.all(sources.map(async src=>{
    const body=await(await fetch(new URL(src,base))).text();
    return {src,raw:Buffer.byteLength(body),gzip:gzipSync(body).length};
  }));
  result.push({url:base,htmlGzip:gzipSync(html).length,initialJsGzip:scripts.reduce((n,s)=>n+s.gzip,0),scripts});
}
mkdirSync(dirname(output),{recursive:true});writeFileSync(output,JSON.stringify(result,null,2));
console.log(result.map(({url,htmlGzip,initialJsGzip,scripts})=>({url,htmlGzip,initialJsGzip,scripts:scripts.length})));
