"use client";

import type { TimelineDTO } from "@signalgraph/shared-types";
import {
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  Bar,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type Props = {
  timeline: TimelineDTO;
};

export function TimelineChart({ timeline }: Props) {
  const data = timeline.points.map((point) => ({
    date: point.date,
    cumulative: point.cumulative_stars,
    delta: point.stars_delta,
  }));

  const suspicious = timeline.suspicious_windows.map((window) => ({
    start: String(window.start),
    end: String(window.end),
  }));

  return (
    <div style={{ width: "100%", height: 360 }}>
      <ResponsiveContainer>
        <ComposedChart data={data} margin={{ top: 10, right: 16, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} />
          <YAxis yAxisId="left" tick={{ fontSize: 11 }} width={44} />
          <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} width={44} />
          <Tooltip />
          <Legend />
          {suspicious.map((window) => (
            <ReferenceArea
              key={`${window.start}-${window.end}`}
              yAxisId="left"
              x1={window.start}
              x2={window.end}
              strokeOpacity={0}
              fill="#f97316"
              fillOpacity={0.12}
            />
          ))}
          <Bar yAxisId="right" dataKey="delta" name="Daily stars" fill="#94a3b8" />
          <Line yAxisId="left" type="monotone" dataKey="cumulative" name="Cumulative stars" stroke="#1d4ed8" dot={false} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}
