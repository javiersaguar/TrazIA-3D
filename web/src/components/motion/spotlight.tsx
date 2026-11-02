"use client";
import { motion, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
export function Spotlight({ size=520,className }: {size?:number;className?:string}) {
 const reduced=useReducedMotion(),[visible,setVisible]=useState(false);
 const x=useSpring(0,{stiffness:120,damping:22,mass:.6}),y=useSpring(0,{stiffness:120,damping:22,mass:.6});
 const transform=useTransform(()=>`translate3d(${x.get()-size/2}px, ${y.get()-size/2}px, 0)`);
 useEffect(()=>{
  if(reduced||!matchMedia("(hover: hover) and (pointer: fine)").matches)return;
  const move=(e:PointerEvent)=>{x.set(e.clientX);y.set(e.clientY);setVisible(true);};
  const leave=()=>setVisible(false);
  window.addEventListener("pointermove",move,{passive:true});document.documentElement.addEventListener("pointerleave",leave);
  return()=>{window.removeEventListener("pointermove",move);document.documentElement.removeEventListener("pointerleave",leave);};
 },[reduced,x,y]);
 return <motion.div aria-hidden data-testid="landing-spotlight" className={cn("landing-spotlight pointer-events-none fixed top-0 left-0 z-[1] rounded-full transition-opacity duration-300",visible&&!reduced?"opacity-100":"opacity-0",className)} style={{width:size,height:size,transform}}/>;
}
