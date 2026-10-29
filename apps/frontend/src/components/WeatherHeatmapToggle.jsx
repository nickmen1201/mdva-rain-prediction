export default function WeatherHeatmapToggle({ enabled, loading, onToggle }) {
  const label = 'Mostrar Lluvia';

  return (
    <button
      type="button"
      className={`map-control-button${enabled ? ' active' : ''}`}
      onClick={onToggle}
      title={label}
      aria-label={label}
      aria-pressed={enabled}
    >
      <span aria-hidden="true">{loading ? '...' : label}</span>
    </button>
  );
}
