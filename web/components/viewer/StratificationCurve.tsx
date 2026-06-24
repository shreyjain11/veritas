"use client";

import { AxisBottom, AxisLeft } from "@visx/axis";
import { curveMonotoneX } from "@visx/curve";
import { Group } from "@visx/group";
import { Area, Circle, LinePath } from "@visx/shape";
import { scaleLinear, scalePoint } from "@visx/scale";
import { useEffect, useRef, useState } from "react";

import type { AuditReport, StratumResult } from "../../lib/audit-report";
import { fmtMetric } from "../../lib/format";
import { Eyebrow } from "../ui";

function useWidth(): [React.RefObject<HTMLDivElement | null>, number] {
  const ref = useRef<HTMLDivElement | null>(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const el = ref.current;
    const update = () => setWidth(el.clientWidth);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  return [ref, width];
}

const AXIS_COLOR = "#80889a"; // --color-faint (WCAG-AA on the panel surface)
const GRID_COLOR = "#1c222a"; // --color-hairline (decorative gridline)
const IRIS = "#9aa2f7";
const DANGER = "#ff9592";

function cleanAxis(name: string): string {
  return name.replace(/^metadata:/, "").replace(/_/g, " ");
}

export function StratificationCurve({ report }: { report: AuditReport }) {
  const [ref, width] = useWidth();
  const strata = [...(report.stratification ?? [])].sort((a, b) => a.bucket_index - b.bucket_index);
  if (strata.length === 0) return null;

  const height = 248;
  const margin = { top: 22, right: 18, bottom: 46, left: 46 };
  const iw = Math.max(0, width - margin.left - margin.right);
  const ih = height - margin.top - margin.bottom;

  const labels = strata.map((s) => s.bucket_label);
  const x = scalePoint<string>({ domain: labels, range: [0, iw], padding: 0.5 });
  const xa = (s: StratumResult) => x(s.bucket_label) ?? 0;

  const ys = strata.flatMap((s) => [
    s.metric.value ?? 0,
    s.metric.ci_low ?? s.metric.value ?? 0,
    s.metric.ci_high ?? s.metric.value ?? 0,
  ]);
  const yMin = Math.min(0, ...ys);
  const yMax = Math.max(...ys);
  const y = scaleLinear({ domain: [yMin, yMax + (yMax - yMin) * 0.12], range: [ih, 0], nice: true });
  const hasCI = strata.some((s) => s.metric.ci_low != null && s.metric.ci_high != null);

  return (
    <section className="border-t border-hairline pt-5">
      <header className="mb-1 flex items-baseline justify-between gap-4">
        <Eyebrow>performance by {cleanAxis(strata[0]?.axis_name ?? "")}</Eyebrow>
        <span className="font-mono text-[0.6875rem] text-muted tnum">
          {strata[0]?.metric.name}
        </span>
      </header>

      <div ref={ref} className="w-full" style={{ minHeight: height }}>
        {width > 0 && (
          <svg width={width} height={height} role="img" aria-label="stratified performance curve">
            <Group left={margin.left} top={margin.top}>
              {y.ticks(4).map((t) => (
                <line key={t} x1={0} x2={iw} y1={y(t)} y2={y(t)} stroke={GRID_COLOR} strokeWidth={1} />
              ))}

              {hasCI && (
                <Area<StratumResult>
                  data={strata}
                  x={(s) => xa(s)}
                  y0={(s) => y(s.metric.ci_low ?? s.metric.value ?? 0)}
                  y1={(s) => y(s.metric.ci_high ?? s.metric.value ?? 0)}
                  curve={curveMonotoneX}
                  fill={IRIS}
                  fillOpacity={0.12}
                />
              )}

              <LinePath<StratumResult>
                data={strata}
                x={(s) => xa(s)}
                y={(s) => y(s.metric.value ?? 0)}
                curve={curveMonotoneX}
                stroke={IRIS}
                strokeWidth={1.5}
                strokeOpacity={0.8}
              />

              {strata.map((s) => {
                const cx = xa(s);
                const cy = y(s.metric.value ?? 0);
                const flagged = s.is_silent_failure;
                return (
                  <Group key={s.bucket_index}>
                    {flagged && <Circle cx={cx} cy={cy} r={7} stroke={DANGER} strokeWidth={1.5} fill="none" />}
                    <Circle cx={cx} cy={cy} r={3.5} fill={flagged ? DANGER : IRIS} />
                    <text
                      x={cx}
                      y={cy - 12}
                      textAnchor="middle"
                      fontFamily="var(--font-mono)"
                      fontSize={11}
                      fill={flagged ? DANGER : "#e8eaed"}
                    >
                      {fmtMetric(s.metric.value)}
                    </text>
                    {flagged && (
                      <text
                        x={cx}
                        y={cy - 26}
                        textAnchor="middle"
                        fontFamily="var(--font-mono)"
                        fontSize={9}
                        fill={DANGER}
                      >
                        silent failure
                      </text>
                    )}
                  </Group>
                );
              })}

              <AxisLeft
                scale={y}
                numTicks={4}
                stroke={AXIS_COLOR}
                hideTicks
                tickLabelProps={{ fill: AXIS_COLOR, fontSize: 10, fontFamily: "var(--font-mono)", dx: -4 }}
              />
              <AxisBottom
                scale={x}
                top={ih}
                stroke={AXIS_COLOR}
                tickStroke={AXIS_COLOR}
                tickLabelProps={{ fill: "#9ca4ae", fontSize: 11, fontFamily: "var(--font-mono)", textAnchor: "middle", dy: 4 }}
              />
              {strata.map((s) => (
                <text
                  key={`n-${s.bucket_index}`}
                  x={xa(s)}
                  y={ih + 34}
                  textAnchor="middle"
                  fontFamily="var(--font-mono)"
                  fontSize={9}
                  fill={AXIS_COLOR}
                >
                  n={s.n}
                </text>
              ))}
            </Group>
          </svg>
        )}
      </div>
    </section>
  );
}
