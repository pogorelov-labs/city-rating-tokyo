import { ReactNode } from 'react';

export default function StatCard({
  label,
  value,
  sub,
  children,
}: {
  label: string;
  value?: string;
  sub?: string;
  children?: ReactNode;
}) {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4">
      <div className="text-xs text-gray-500 mb-1">{label}</div>
      {value && <div className="text-xl font-bold">{value}</div>}
      {children}
      {sub && <div className="text-xs text-gray-400">{sub}</div>}
    </div>
  );
}
