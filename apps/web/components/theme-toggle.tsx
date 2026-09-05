'use client';
import { Moon, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

export function ThemeToggle() {
  const [dark,setDark]=useState(true);
  useEffect(()=>{const value=localStorage.getItem('dias-theme');const next=value?value==='dark':true;setDark(next);document.documentElement.classList.toggle('dark',next)},[]);
  const toggle=()=>{const next=!dark;setDark(next);document.documentElement.classList.toggle('dark',next);localStorage.setItem('dias-theme',next?'dark':'light')};
  return <button className="icon-button" onClick={toggle} aria-label={`Switch to ${dark?'light':'dark'} mode`}>{dark?<Sun size={18}/>:<Moon size={18}/>}</button>;
}
