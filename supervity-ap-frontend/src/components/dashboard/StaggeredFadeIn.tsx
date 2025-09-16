"use client";
import { motion } from "framer-motion";

const containerVariants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  hidden: { y: 20, opacity: 0 },
  visible: {
    y: 0,
    opacity: 1,
    transition: {
      duration: 0.5,
    },
  },
};

export const StaggeredFadeIn = ({
  children,
}: {
  children: React.ReactNode;
}) => (
  <motion.div variants={containerVariants} initial="hidden" animate="visible">
    {children}
  </motion.div>
);

export const FadeInItem = ({ children }: { children: React.ReactNode }) => (
  <motion.div variants={itemVariants}>{children}</motion.div>
);
