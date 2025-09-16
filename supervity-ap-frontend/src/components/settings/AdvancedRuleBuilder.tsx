"use client";
import React from "react";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { PlusCircle, Trash2 } from "lucide-react";
import { cn } from "@/lib/utils";

// Define the shape of a single condition
export interface Condition {
  field: string;
  operator: string;
  value: string | number;
}

// Define the overall policy structure
export interface Policy {
  logical_operator: "AND" | "OR";
  conditions: Condition[];
}

// --- Configuration for available fields and operators ---
const FIELD_OPTIONS = [
  { value: "grand_total", label: "Invoice Total", type: "number" },
  { value: "vendor_name", label: "Vendor Name", type: "text" },
  { value: "invoice_date", label: "Invoice Date", type: "date" },
  { value: "due_date", label: "Due Date", type: "date" },
  {
    value: "status",
    label: "Status",
    type: "select",
    options: [
      "needs_review",
      "on_hold",
      "matched",
      "rejected",
      "paid",
      "ingested",
      "matching",
    ],
  },
  { value: "subtotal", label: "Subtotal", type: "number" },
  { value: "tax", label: "Tax Amount", type: "number" },
  { value: "buyer_name", label: "Buyer Name", type: "text" },
  { value: "payment_terms", label: "Payment Terms", type: "text" },
];

const OPERATOR_OPTIONS: Record<string, { value: string; label: string }[]> = {
  number: [
    { value: ">", label: ">" },
    { value: "<", label: "<" },
    { value: ">=", label: "≥" },
    { value: "<=", label: "≤" },
    { value: "equals", label: "=" },
    { value: "not_equals", label: "≠" },
  ],
  text: [
    { value: "equals", label: "is" },
    { value: "contains", label: "contains" },
    { value: "not_equals", label: "is not" },
  ],
  date: [
    { value: "equals", label: "is" },
    { value: ">", label: "is after" },
    { value: "<", label: "is before" },
    { value: "is_within_next_days", label: "is within next N days" },
  ],
  select: [
    { value: "equals", label: "is" },
    { value: "not_equals", label: "is not" },
  ],
};

interface RuleBuilderProps {
  policy: Policy | null | undefined; // --- ALLOW NULL/UNDEFINED ---
  onPolicyChange: (updatedPolicy: Policy) => void;
}

export const AdvancedRuleBuilder = ({
  policy,
  onPolicyChange,
}: RuleBuilderProps) => {
  // --- START: ROBUST STATE HANDLING ---
  // If policy or conditions are not defined, use a default empty state.
  const conditions = policy?.conditions ?? [];
  const logicalOperator = policy?.logical_operator ?? "AND";

  const handleConditionChange = (
    index: number,
    key: keyof Condition,
    value: string | number,
  ) => {
    const updatedConditions = [...conditions];
    updatedConditions[index] = { ...updatedConditions[index], [key]: value };

    // If field changes, reset operator and value
    if (key === "field") {
      updatedConditions[index].operator = "";
      updatedConditions[index].value = "";
    }
    onPolicyChange({
      logical_operator: logicalOperator,
      conditions: updatedConditions,
    });
  };

  const addCondition = () => {
    onPolicyChange({
      logical_operator: logicalOperator,
      conditions: [...conditions, { field: "", operator: "", value: "" }],
    });
  };

  const removeCondition = (index: number) => {
    const updatedConditions = conditions.filter((_, i) => i !== index);
    onPolicyChange({
      logical_operator: logicalOperator,
      conditions: updatedConditions,
    });
  };

  const setLogicalOperator = (op: "AND" | "OR") => {
    onPolicyChange({ logical_operator: op, conditions: conditions });
  };
  // --- END: ROBUST STATE HANDLING ---

  return (
    <div className="space-y-4 p-4 border rounded-lg bg-gray-50/70">
      {/* --- USE THE SAFE `conditions` VARIABLE --- */}
      {conditions.map((condition, index) => {
        const selectedField = FIELD_OPTIONS.find(
          (f) => f.value === condition.field,
        );
        const key = `${index}-${condition.field}`; // Stable key for re-renders

        return (
          <div key={key} className="flex items-center gap-2">
            {index > 0 && (
              <div className="w-12 text-center">
                <select
                  value={logicalOperator}
                  onChange={(e) =>
                    setLogicalOperator(e.target.value as "AND" | "OR")
                  }
                  className="text-xs font-bold bg-white border-gray-300 rounded-md p-1"
                >
                  <option>AND</option>
                  <option>OR</option>
                </select>
              </div>
            )}
            <div
              className={cn(
                "grid grid-cols-3 gap-2 flex-grow",
                index === 0 && "ml-[60px]",
              )}
            >
              <select
                value={condition.field || ""}
                onChange={(e) =>
                  handleConditionChange(index, "field", e.target.value)
                }
                className="h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
              >
                <option value="" disabled>
                  Select a field...
                </option>
                {FIELD_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>

              <select
                value={condition.operator || ""}
                onChange={(e) =>
                  handleConditionChange(index, "operator", e.target.value)
                }
                className="h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                disabled={!selectedField}
              >
                <option value="" disabled>
                  Select operator...
                </option>
                {selectedField &&
                  OPERATOR_OPTIONS[selectedField.type].map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
              </select>

              {selectedField?.type === "select" ? (
                <select
                  value={String(condition.value || "")}
                  onChange={(e) =>
                    handleConditionChange(index, "value", e.target.value)
                  }
                  className="h-10 rounded-md border border-gray-300 bg-white px-3 py-2 text-sm"
                >
                  <option value="" disabled>
                    Select a value...
                  </option>
                  {selectedField.options?.map((opt) => (
                    <option key={opt} value={opt}>
                      {opt}
                    </option>
                  ))}
                </select>
              ) : (
                <Input
                  type={
                    selectedField?.type === "number"
                      ? "number"
                      : selectedField?.type === "date"
                        ? "date"
                        : "text"
                  }
                  value={String(condition.value || "")}
                  onChange={(e) =>
                    handleConditionChange(index, "value", e.target.value)
                  }
                  className="bg-white"
                  disabled={!selectedField}
                />
              )}
            </div>
            <Button
              type="button"
              variant="ghost"
              size="sm"
              onClick={() => removeCondition(index)}
            >
              <Trash2 className="h-4 w-4 text-red-500" />
            </Button>
          </div>
        );
      })}
      <Button
        type="button"
        variant="secondary"
        size="sm"
        onClick={addCondition}
      >
        <PlusCircle className="mr-2 h-4 w-4" /> Add Condition
      </Button>
    </div>
  );
};
