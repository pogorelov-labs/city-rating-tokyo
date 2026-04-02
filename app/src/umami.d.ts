interface Window {
  umami?: {
    track: (event: string, data?: Record<string, string | number>) => void;
    identify: (data: Record<string, string>) => void;
  };
}
