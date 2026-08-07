import { Tooltip as MuiTooltip } from "@mui/material";

export default function Tooltip({ tooltipProps = {}, children }) {
  return <MuiTooltip {...tooltipProps}>{children}</MuiTooltip>;
}
