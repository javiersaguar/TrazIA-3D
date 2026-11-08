// Perfil reproducible de la entrada. Chrome software + CPU limitada; no mide la RTX ni Vercel.
import { chromium } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";

const url=process.argv[2]??"http://127.0.0.1:3120/";
const output=resolve(process.argv[3]??"../generated/intro-profile.json");
const browser=await chromium.launch({channel:"chrome",args:["--use-angle=swiftshader","--enable-unsafe-swiftshader"]});
const runs=[];
for(let i=0;i<3;i++){
  const context=await browser.newContext({viewport:{width:1600,height:940},reducedMotion:"no-preference"});
  const page=await context.newPage(),cdp=await context.newCDPSession(page);
  await cdp.send("Emulation.setCPUThrottlingRate",{rate:4});
  await page.addInitScript(()=>{
    window.introProfile={frames:[],tasks:[],canvases:[],phases:[],hydrated:null};
    const data=window.introProfile;
    new PerformanceObserver(list=>data.tasks.push(...list.getEntries().map(e=>({at:e.startTime,ms:e.duration})))).observe({type:"longtask",buffered:true});
    const tick=now=>{data.frames.push(now);if(now<12000)requestAnimationFrame(tick);};requestAnimationFrame(tick);
    let previous="",seen=0,oldSourceSeen=false;
    new MutationObserver(()=>{
      const phase=document.querySelector("[data-intro-phase]")?.getAttribute("data-intro-phase");
      if(phase&&phase!==previous){data.phases.push({phase,at:performance.now()});previous=phase;}
      if (!phase) {
        const oldSource=document.querySelector(".fixed.cursor-pointer");
        if(oldSource)oldSourceSeen=true;
        if(oldSourceSeen&&!oldSource&&previous!=="flying") {
          data.phases.push({phase:"flying",at:performance.now(),detection:"source-removal"});previous="flying";
        }
      }
      const count=document.querySelectorAll("canvas").length;
      if(count>seen){data.canvases.push({at:performance.now(),count});seen=count;}
    }).observe(document,{subtree:true,childList:true,attributes:true,attributeFilter:["data-intro-phase"]});
  });
  await page.goto(url);
  await page.getByRole("button",{name:/Saltar intro/}).waitFor({state:"visible"});
  const began=await page.evaluate(()=>performance.now());
  await page.getByRole("button",{name:/Saltar intro/}).waitFor({state:"hidden",timeout:30000});
  await page.waitForTimeout(1800);
  const raw=await page.evaluate(()=>window.introProfile);
  const phase=raw.phases.find(p=>p.phase==="flying");
  const start=phase?.at??began+1900,end=start+800;
  const gaps=raw.frames.slice(1).map((t,j)=>({at:t,ms:t-raw.frames[j]})).filter(f=>f.at>=start&&f.at<=end);
  const tasks=raw.tasks.filter(t=>t.at<end&&t.at+t.ms>start);
  runs.push({flightWindowMs:[start,end],windowSource:phase?(phase.detection??"explicit-phase"):"approximation-baseline",maxFrameGapMs:Math.max(0,...gaps.map(g=>g.ms)),framesOver50ms:gaps.filter(g=>g.ms>50).length,
    blockingMs:tasks.reduce((sum,t)=>sum+Math.max(0,Math.min(t.at+t.ms,end)-Math.max(t.at,start)),0),...raw});
  await context.close();
}
await browser.close();
mkdirSync(dirname(output),{recursive:true});
writeFileSync(output,JSON.stringify({url,cpuThrottle:4,renderer:"SwiftShader",runs},null,2));
console.log(JSON.stringify(runs.map(({maxFrameGapMs,framesOver50ms,blockingMs,canvases,phases})=>({maxFrameGapMs,framesOver50ms,blockingMs,canvases,phases})),null,2));
