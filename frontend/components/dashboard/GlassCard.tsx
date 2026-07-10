import React from 'react';

export const GlassCard = ({ children, className = '', onClick }: { children: React.ReactNode; className?: string; onClick?: () => void }) => (
  <div
    onClick={onClick}
    className={`bg-[#FFFFFF]/60 backdrop-blur-xl border border-[#E2E8F0]/30 rounded-xl overflow-hidden ${onClick ? 'cursor-pointer hover:border-violet-500/50 hover:shadow-[0_0_20px_rgba(139,92,246,0.15)] transition-all duration-300' : ''} ${className}`}
  >
    {children}
  </div>
);
