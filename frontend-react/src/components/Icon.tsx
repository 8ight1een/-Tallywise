export default function Icon({ name }: { name: string }) {
  return (
    <svg className="icon" aria-hidden="true">
      <use href={'/icons.svg#i-' + name} />
    </svg>
  )
}
