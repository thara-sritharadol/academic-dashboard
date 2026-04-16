export const getDynamicColor = (index: number, alpha: number = 1) => {
  const hue = (index * 137.508) % 360;
  return `hsla(${hue}, 70%, 50%, ${alpha})`;
};
