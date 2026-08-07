import { Stack as MuiStack } from "@mui/material";

export default function Stack({ stackProps = {}, children }) {
  // MuiStack processes system props (direction, gap, spacing, etc.) via sx
  // We need to ensure MUI system props are passed correctly
  const {
    direction, justifyContent, alignItems, spacing, gap, flexWrap,
    mt, mb, ml, mr, mx, my, pt, pb, pl, pr, px, py,
    className, onClick, sx,
    ...otherProps
  } = stackProps;

  return (
    <MuiStack
      direction={direction}
      justifyContent={justifyContent}
      alignItems={alignItems}
      spacing={spacing}
      className={className}
      onClick={onClick}
      sx={{
        gap,
        flexWrap,
        mt, mb, ml, mr, mx, my,
        pt, pb, pl, pr, px, py,
        ...sx,
      }}
      {...otherProps}
    >
      {children}
    </MuiStack>
  );
}
