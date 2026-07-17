import { useEffect, useState } from "react";

function formatCountdown(remainingMinutes) {
  const totalSeconds = Math.max(0, Math.round(remainingMinutes * 60));
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m} min ${s.toString().padStart(2, "0")} sec`;
}

export default function WarRoomBanner({ blinkingTickets, onTakeAction }) {
  const [tick, setTick] = useState(Date.now());

  useEffect(() => {
    if (blinkingTickets.length === 0) return undefined;
    const id = setInterval(() => setTick(Date.now()), 1000);
    return () => clearInterval(id);
  }, [blinkingTickets.length]);

  if (blinkingTickets.length === 0) return null;

  const worst = blinkingTickets[0];
  const secondsElapsed = (tick - worst.fetchedAt) / 1000;
  const liveRemaining = worst.remaining_minutes - secondsElapsed / 60;

  return (
    <div className="war-room-banner">
      🚨 CRITICAL: {worst.ticket_number} breaches in {formatCountdown(liveRemaining)} — {worst.customer} — Action Required
      {blinkingTickets.length > 1 && ` (+${blinkingTickets.length - 1} more)`}
      <button className="btn" onClick={() => onTakeAction(worst)}>
        Take Action
      </button>
    </div>
  );
}
