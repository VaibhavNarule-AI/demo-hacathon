export default function Logo({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
      <path
        d="M24 4 L42 11 V22 C42 33 34.5 41.5 24 44 C13.5 41.5 6 33 6 22 V11 Z"
        fill="var(--accent-soft)"
        stroke="var(--accent)"
        strokeWidth="2.2"
        strokeLinejoin="round"
      />
      <path
        d="M11 25 H18 L21 18 L26 32 L29 22 L31 25 H37"
        fill="none"
        stroke="var(--accent)"
        strokeWidth="2.4"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
