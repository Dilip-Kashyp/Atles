import { Button as MuiButton } from "@mui/material";

export default function Button({ buttonProps = {}, children, ...rest }) {
  return (
    <MuiButton {...buttonProps} {...rest}>
      {children ?? buttonProps.children}
    </MuiButton>
  );
}
