export default function CenterButton({ active, onClick }) {
  return (
    <button
      type="button"
      className={`map-control-button${active ? ' active' : ''}`}
      onClick={onClick}
      title="Centrar en mi ubicacion"
      aria-label="Centrar en mi ubicacion"
      aria-pressed={active}
    >
      <span aria-hidden="true">Centrar</span>
    </button>
  );
}
