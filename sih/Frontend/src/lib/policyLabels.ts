import type { PolicyType } from "../types/contract";

/**
 * The one vocabulary for policy_type strings a judge might see - the Dashboard, Simulations,
 * Experiments and Models tabs all import this rather than keeping their own copy, so "q_learning"
 * never leaks onto screen in one tab while another already translates it.
 */
export const POLICY_LABELS: Record<PolicyType, string> = {
  baseline: "Fixed sweep",
  random: "Random",
  bandit: "Bandit",
  q_learning: "Q-learning",
  dqn: "DQN",
  ppo: "PPO",
  index: "Index (SCT)",
  ctmc: "CTMC floor",
};

/** Falls back to the raw string for anything outside the contract's policy_type enum. */
export const policyLabel = (policy: string): string =>
  POLICY_LABELS[policy as PolicyType] ?? policy;
