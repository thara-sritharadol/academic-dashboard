export const getDynamicColor = (index: number) => {
  const hue = (index * 137.508) % 360;
  return `hsl(${hue}, 70%, 50%)`;
};
