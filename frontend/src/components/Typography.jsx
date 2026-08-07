import { Typography as MuiTypography } from "@mui/material";

export default function Typography({ typographyProps = {}, children, ...rest }) {
  const mergedProps = { ...typographyProps, ...rest };
  return (
    <MuiTypography {...mergedProps}>
      {mergedProps.children ?? children}
    </MuiTypography>
  );
}
