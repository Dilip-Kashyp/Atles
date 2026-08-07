import { LinearProgress as MuiLinearProgress } from "@mui/material";

export default function LinearProgress({ linearProgressProps = {} }) {
  return <MuiLinearProgress {...linearProgressProps} />;
}
