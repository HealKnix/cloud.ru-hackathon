import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type CSSProperties,
  type PropsWithChildren,
} from 'react';
import { cn } from '../lib/utils';

type ChannelSelector = 'R' | 'G' | 'B';

export type LiquidGlassOptions = {
  width?: number;
  height?: number;
  radius?: number;
  border?: number;
  lightness?: number;
  alpha?: number;
  blur?: number;
  displace?: number;
  scale?: number;
  frost?: number;
  saturation?: number;
  r?: number;
  g?: number;
  b?: number;
  xChannel?: ChannelSelector;
  yChannel?: ChannelSelector;
  blend?:
    | 'normal'
    | 'multiply'
    | 'screen'
    | 'overlay'
    | 'darken'
    | 'lighten'
    | 'color-dodge'
    | 'color-burn'
    | 'hard-light'
    | 'soft-light'
    | 'difference'
    | 'exclusion'
    | 'hue'
    | 'saturation'
    | 'color'
    | 'luminosity'
    | 'plus-darker'
    | 'plus-lighter';
};

type LiquidGlassProps = PropsWithChildren<{
  className?: string;
  tint?: string;
  options?: LiquidGlassOptions;
  debug?: boolean;
}>;

const defaultOptions: Required<LiquidGlassOptions> = {
  width: 360,
  height: 160,
  radius: 18,
  border: 0.08,
  lightness: 55,
  alpha: 0.9,
  blur: 10,
  displace: 0.35,
  scale: -220,
  frost: 0.08,
  saturation: 1.15,
  r: 0,
  g: 10,
  b: 20,
  xChannel: 'R',
  yChannel: 'G',
  blend: 'difference',
};

const clampDimension = (value: number) => Math.max(1, Math.round(value));

const createDisplacementMap = (opts: Required<LiquidGlassOptions>) => {
  const width = clampDimension(opts.width);
  const height = clampDimension(opts.height);
  const border = Math.min(width, height) * (opts.border * 0.5);
  const clampedBorder = Math.max(
    0,
    Math.min(border, Math.min(width, height) / 2),
  );
  const innerWidth = Math.max(0, width - clampedBorder * 2);
  const innerHeight = Math.max(0, height - clampedBorder * 2);

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}">
      <defs>
        <linearGradient id="liquid-red" x1="100%" y1="0%" x2="0%" y2="0%">
          <stop offset="0%" stop-color="#000"/>
          <stop offset="100%" stop-color="red"/>
        </linearGradient>
        <linearGradient id="liquid-blue" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stop-color="#000"/>
          <stop offset="100%" stop-color="blue"/>
        </linearGradient>
      </defs>
      <rect x="0" y="0" width="${width}" height="${height}" fill="black"></rect>
      <rect x="0" y="0" width="${width}" height="${height}" rx="${opts.radius}" fill="url(#liquid-red)" />
      <rect x="0" y="0" width="${width}" height="${height}" rx="${opts.radius}" fill="url(#liquid-blue)" style="mix-blend-mode: ${opts.blend}" />
      <rect
        x="${clampedBorder}"
        y="${clampedBorder}"
        width="${innerWidth}"
        height="${innerHeight}"
        rx="${opts.radius}"
        fill="hsl(0 0% ${opts.lightness}% / ${opts.alpha})"
        style="filter:blur(${opts.blur}px)"
      />
    </svg>
  `;

  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
};

const buildBackdropFilter = (id: string, saturation: number) =>
  `url(#${id}) saturate(${saturation})`;

export const LiquidGlass = ({
  children,
  className,
  tint,
  options,
  debug,
}: LiquidGlassProps) => {
  const id = useId();
  const filterId = useMemo(() => `liquid-glass-${id}`, [id]);
  const surfaceRef = useRef<HTMLDivElement>(null);
  const [measuredSize, setMeasuredSize] = useState({
    width: defaultOptions.width,
    height: defaultOptions.height,
  });

  useEffect(() => {
    const node = surfaceRef.current;
    if (!node) return;

    const updateSize = () => {
      const rect = node.getBoundingClientRect();
      const width = clampDimension(rect.width || defaultOptions.width);
      const height = clampDimension(rect.height || defaultOptions.height);
      setMeasuredSize((prev) =>
        prev.width === width && prev.height === height
          ? prev
          : { width, height },
      );
    };

    updateSize();
    const resizeObserver = new ResizeObserver(updateSize);
    resizeObserver.observe(node);

    return () => resizeObserver.disconnect();
  }, []);

  const resolved = useMemo(() => {
    const merged = { ...defaultOptions, ...options };
    const width = options?.width ?? measuredSize.width ?? defaultOptions.width;
    const height =
      options?.height ?? measuredSize.height ?? defaultOptions.height;

    return {
      ...merged,
      width: clampDimension(width),
      height: clampDimension(height),
      xChannel: (merged.xChannel ?? 'R').toUpperCase() as ChannelSelector,
      yChannel: (merged.yChannel ?? 'G').toUpperCase() as ChannelSelector,
    };
  }, [measuredSize.height, measuredSize.width, options]);

  const mapHref = useMemo(() => createDisplacementMap(resolved), [resolved]);
  const backdropValue = useMemo(
    () => buildBackdropFilter(filterId, resolved.saturation),
    [filterId, resolved.saturation],
  );

  const surfaceStyle: CSSProperties = {
    borderRadius: `${resolved.radius}px`,
    overflow: 'hidden',
    position: 'relative',
    backdropFilter: backdropValue,
    WebkitBackdropFilter: backdropValue,
    backgroundColor: `color-mix(in srgb, transparent, ${
      tint ? tint : 'hsl(var(--heroui-content1))'
    } ${resolved.frost * 100}%)`,
    boxShadow: `0 0 2px color-mix(in srgb, transparent, hsl(var(--heroui-foreground)) 5%) inset, 0 0 10px color-mix(in srgb, transparent, hsl(var(--heroui-foreground)) 4%) inset, 0 8px 24px rgba(0, 0, 0, 0.08)`,
    isolation: 'isolate',
  };

  const filterStyle: CSSProperties = {
    width: '100%',
    height: '100%',
    pointerEvents: 'none',
    position: 'absolute',
    inset: 0,
  };

  return (
    <div
      ref={surfaceRef}
      className={cn('relative', className)}
      style={surfaceStyle}
    >
      {children}

      <svg
        aria-hidden
        className="pointer-events-none absolute inset-0 h-0 w-0"
        style={filterStyle}
      >
        <defs>
          <filter id={filterId} colorInterpolationFilters="sRGB">
            <feImage
              x="0"
              y="0"
              width="100%"
              height="100%"
              preserveAspectRatio="none"
              href={mapHref}
              result="map"
            />
            <feDisplacementMap
              in="SourceGraphic"
              in2="map"
              xChannelSelector={resolved.xChannel}
              yChannelSelector={resolved.yChannel}
              scale={resolved.scale + resolved.r}
              result="dispRed"
            />
            <feDisplacementMap
              in="SourceGraphic"
              in2="map"
              xChannelSelector={resolved.xChannel}
              yChannelSelector={resolved.yChannel}
              scale={resolved.scale + resolved.g}
              result="dispGreen"
            />
            <feDisplacementMap
              in="SourceGraphic"
              in2="map"
              xChannelSelector={resolved.xChannel}
              yChannelSelector={resolved.yChannel}
              scale={resolved.scale + resolved.b}
              result="dispBlue"
            />
            {/* <feColorMatrix
              in="dispRed"
              type="matrix"
              values="1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0"
              result="red"
            /> */}
            {/* <feColorMatrix
              in="dispGreen"
              type="matrix"
              values="0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 1 0"
              result="green"
            /> */}
            {/* <feColorMatrix
              in="dispBlue"
              type="matrix"
              values="0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 1 0"
              result="blue"
            /> */}
            {/* <feBlend in="red" in2="green" mode="screen" result="rg" /> */}
            {/* <feBlend in="rg" in2="blue" mode="screen" result="output" /> */}
            <feGaussianBlur in="output" stdDeviation={resolved.displace} />
          </filter>
        </defs>
      </svg>

      {debug && (
        <div className="border-default-100/60 pointer-events-none absolute -bottom-14 right-2 w-32 rounded-lg border bg-black/10 p-1 shadow-sm backdrop-blur">
          <img
            src={mapHref}
            alt="Displacement map preview"
            className="h-full w-full rounded"
          />
        </div>
      )}
    </div>
  );
};

LiquidGlass.displayName = 'LiquidGlass';

export default LiquidGlass;
