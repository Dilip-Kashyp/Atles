import { Container as MuiContainer } from "@mui/material";

export default function Container({ containerProps = {}, children, ...rest }) {
  return <MuiContainer {...containerProps} {...rest}>{children}</MuiContainer>;
}
