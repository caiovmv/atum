import { useState, useEffect, useRef, useCallback, type ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { IoChevronForward, IoChevronBack } from 'react-icons/io5';
import './ContentRail.css';

export interface ContentRailProps<T> {
  title: string;
  linkTo?: string;
  items: T[];
  renderItem: (item: T) => ReactNode;
  getKey: (item: T) => string;
}

export function ContentRail<T>({ title, linkTo, items, renderItem, getKey }: ContentRailProps<T>) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [canScrollLeft, setCanScrollLeft] = useState(false);
  const [canScrollRight, setCanScrollRight] = useState(false);

  const checkScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    setCanScrollLeft(el.scrollLeft > 4);
    setCanScrollRight(el.scrollLeft + el.clientWidth < el.scrollWidth - 4);
  }, []);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    checkScroll();
    el.addEventListener('scroll', checkScroll, { passive: true });
    const ro = new ResizeObserver(checkScroll);
    ro.observe(el);
    return () => {
      el.removeEventListener('scroll', checkScroll);
      ro.disconnect();
    };
  }, [checkScroll, items.length]);

  const scroll = (dir: number) => {
    scrollRef.current?.scrollBy({ left: dir * 320, behavior: 'smooth' });
  };

  if (items.length === 0) return null;

  return (
    <section className="content-rail" aria-label={title}>
      <div className="content-rail-header">
        <h2 className="content-rail-title">{title}</h2>
        {linkTo && (
          <Link to={linkTo} className="content-rail-link">
            Ver tudo <IoChevronForward size={14} />
          </Link>
        )}
      </div>
      <div className="content-rail-scroll-wrap">
        {canScrollLeft && (
          <button
            type="button"
            className="content-rail-arrow content-rail-arrow--left"
            onClick={() => scroll(-1)}
            aria-label="Anterior"
          >
            <IoChevronBack size={20} />
          </button>
        )}
        <div className="content-rail-row" ref={scrollRef}>
          {items.map((item) => (
            <div key={getKey(item)} className="content-rail-card-wrap">
              {renderItem(item)}
            </div>
          ))}
        </div>
        {canScrollRight && (
          <button
            type="button"
            className="content-rail-arrow content-rail-arrow--right"
            onClick={() => scroll(1)}
            aria-label="Próximo"
          >
            <IoChevronForward size={20} />
          </button>
        )}
      </div>
    </section>
  );
}
