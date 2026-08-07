import { Box as MuiBox } from "@mui/material";

export default function Box({ boxProps = {}, children }) {
  // MuiBox processes all system props through sx.
  // Extract known MUI props that should be passed directly.
  const { component, className, onClick, onMouseEnter, onMouseLeave, sx, ...systemProps } = boxProps;

  return (
    <MuiBox
      component={component}
      className={className}
      onClick={onClick}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
      sx={{ ...systemProps, ...sx }}
    >
      {children}
    </MuiBox>
  );
}
