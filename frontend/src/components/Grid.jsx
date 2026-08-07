import { Grid as MuiGrid } from "@mui/material";

export default function Grid({ gridProps = {}, children, ...rest }) {
  return <MuiGrid {...gridProps} {...rest}>{children}</MuiGrid>;
}
