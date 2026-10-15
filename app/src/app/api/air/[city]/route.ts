import { getLiveAir } from '@/lib/air/live';
export const dynamic = 'force-dynamic';
export async function GET(_request: Request, { params }: { params: Promise<{ city: string }> }) {
  const { city } = await params;
  if (city !== 'tokyo' && city !== 'bangkok') return Response.json({ error: 'Unknown city' }, { status: 404 });
  return Response.json(await getLiveAir(city), { headers: { 'Cache-Control': 'no-store' } });
}
