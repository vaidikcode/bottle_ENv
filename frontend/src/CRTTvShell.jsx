export default function CRTTvShell({ children }) {
  return (
    <div className="crtTvViewport">
      <div className="crtTvGlass" />
      <div className="crtTvBloom" />
      <div className="crtTvScanlines" />
      <div className="crtTvRgbShift" />
      <div className="crtTvVignette" />
      <div className="crtTvReflection" />
      <div className="crtTvFlicker" />
      <div className="crtTvContent">{children}</div>
    </div>
  );
}
