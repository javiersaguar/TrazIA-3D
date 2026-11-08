"use client";
import { motion, useReducedMotion, useSpring, useTransform } from "motion/react";
import { useEffect, useState, useRef } from "react";
import { cn } from "@/lib/cn";
export function Spotlight({ size=520,className }: {size?:number;className?:string}) {
 const entered = useRef(false);
 const reduced=useReducedMotion(),[visible,setVisible]=useState(false);
 const x=useSpring(0,{stiffness:120,damping:22,mass:.6}),y=useSpring(0,{stiffness:120,damping:22,mass:.6});
 const transform=useTransform(()=>`translate3d(${x.get()-size/2}px, ${y.get()-size/2}px, 0)`);
 useEffect(()=>{
  if(reduced||!matchMedia("(hover: hover) and (pointer: fine)").matches)return;
  let frame=0, px=0, py=0;
  const move=(e:PointerEvent)=>{
    px=e.clientX; py=e.clientY;
    if(!entered.current){entered.current=true;setVisible(true);}
    if(!frame)frame=requestAnimationFrame(()=>{frame=0;x.set(px);y.set(py);});
  };
  const leave=()=>{entered.current=false;setVisible(false);};
  window.addEventListener("pointermove",move,{passive:true});document.documentElement.addEventListener("pointerleave",leave);
  return()=>{cancelAnimationFrame(frame);window.removeEventListener("pointermove",move);document.documentElement.removeEventListener("pointerleave",leave);};
 },[reduced,x,y]);
 return <motion.div aria-hidden data-testid="landing-spotlight" className={cn("landing-spotlight pointer-events-none fixed top-0 left-0 z-[1] rounded-full transition-opacity duration-300",visible&&!reduced?"opacity-100":"opacity-0",className)} style={{width:size,height:size,transform,contain:"strict",willChange:"transform"}}/>;
}
