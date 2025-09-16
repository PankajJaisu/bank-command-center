"use client";

import { Input } from "./Input";
import { type DateRange } from "@/lib/api";

interface DateRangePickerProps {
  value: DateRange;
  onValueChange: (range: DateRange) => void;
}

export const DateRangePicker = ({
  value,
  onValueChange,
}: DateRangePickerProps) => {
  return (
    <div className="flex items-center gap-2 bg-white p-2 rounded-lg border">
      <Input
        type="date"
        value={value.from || ""}
        onChange={(e) =>
          onValueChange({ ...value, from: e.target.value || null })
        }
        className="text-gray-medium border-none"
      />
      <span className="text-gray-medium">to</span>
      <Input
        type="date"
        value={value.to || ""}
        onChange={(e) =>
          onValueChange({ ...value, to: e.target.value || null })
        }
        className="text-gray-medium border-none"
      />
    </div>
  );
};
