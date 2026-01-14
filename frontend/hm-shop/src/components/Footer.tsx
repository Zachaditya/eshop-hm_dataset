export default function Footer() {
  return (
    <footer className="border-t border-border bg-white">
      <div className="mx-auto max-w-5xl px-4 py-8">
        <div className="flex flex-col gap-2 text-sm text-neutral-600 sm:flex-row sm:items-center sm:justify-between">
          <p>© {new Date().getFullYear()} Ecommerce Portfolio Project </p>
          <div className="flex gap-4">
            <a className="hover:text-neutral-900" href="#">
              About
            </a>
            <a className="hover:text-neutral-900" href="#">
              Contact
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
}
