import { Skeleton as MuiSkeleton } from "@mui/material";

export default function Skeleton({ skeletonProps = {} }) {
  return <MuiSkeleton {...skeletonProps} />;
}
