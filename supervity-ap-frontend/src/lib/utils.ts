import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { type Policy, type Condition } from "@/components/settings/AdvancedRuleBuilder";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// --- ADD NEW FUNCTION ---
export function formatRule(policy: Policy): string {
  if (!policy || !policy.conditions || policy.conditions.length === 0) {
    return 'No conditions set';
  }

  const formatCondition = (cond: Condition) => {
    const fieldLabel = cond.field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
    let operatorLabel = cond.operator;
    
    // Make operators more readable
    switch (cond.operator) {
      case 'equals':
        operatorLabel = 'is';
        break;
      case 'not_equals':
        operatorLabel = 'is not';
        break;
      case 'contains':
        operatorLabel = 'contains';
        break;
      case 'is_within_next_days':
        operatorLabel = 'is within next';
        break;
      default:
        operatorLabel = cond.operator;
    }
    
    let valueLabel = String(cond.value);
    if (cond.operator === 'is_within_next_days') {
      valueLabel = `${cond.value} days`;
    }
    
    return `${fieldLabel} ${operatorLabel} "${valueLabel}"`;
  };

  const operatorStr = ` ${policy.logical_operator} `;
  return policy.conditions.map(formatCondition).join(operatorStr);
} 