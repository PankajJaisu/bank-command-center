"use client";

import { useState, useEffect, useMemo } from "react";
import {
  getExtractionFieldConfigurations,
  updateExtractionFieldConfigurations,
  type ExtractionFieldConfig,
  type ExtractionFieldConfigUpdate,
} from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";
import { Checkbox } from "@/components/ui/Checkbox";
import { Button } from "@/components/ui/Button";
import { Loader2, Save } from "lucide-react";
import toast from "react-hot-toast";
import { cn } from "@/lib/utils";

export const ConfigureExtractionTab = () => {
  const [configs, setConfigs] = useState<ExtractionFieldConfig[]>([]);
  const [originalConfigs, setOriginalConfigs] = useState<
    ExtractionFieldConfig[]
  >([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    setIsLoading(true);
    getExtractionFieldConfigurations()
      .then((data) => {
        setConfigs(data);
        setOriginalConfigs(data); // Keep a copy for diffing
      })
      .catch(() => toast.error("Failed to load field configurations."))
      .finally(() => setIsLoading(false));
  }, []);

  const handleToggle = (id: number) => {
    setConfigs((prev) =>
      prev.map((config) =>
        config.id === id
          ? { ...config, is_enabled: !config.is_enabled }
          : config,
      ),
    );
  };

  const handleSaveChanges = async () => {
    setIsSaving(true);
    const changes: ExtractionFieldConfigUpdate[] = configs
      .filter(
        (current, index) =>
          current.is_enabled !== originalConfigs[index].is_enabled,
      )
      .map(({ id, is_enabled }) => ({ id, is_enabled }));

    if (changes.length === 0) {
      toast.success("No changes to save.");
      setIsSaving(false);
      return;
    }

    try {
      await updateExtractionFieldConfigurations(changes);
      toast.success("Configurations saved successfully!");
      setOriginalConfigs(configs); // Update original state after successful save
    } catch (error) {
      toast.error(
        `Save failed: ${error instanceof Error ? error.message : "Unknown error"}`,
      );
    } finally {
      setIsSaving(false);
    }
  };

  const hasChanges = useMemo(() => {
    return JSON.stringify(configs) !== JSON.stringify(originalConfigs);
  }, [configs, originalConfigs]);

  const groupedConfigs = useMemo(() => {
    return configs.reduce(
      (acc, config) => {
        const docType = config.document_type;
        if (!acc[docType]) {
          acc[docType] = [];
        }
        acc[docType].push(config);
        return acc;
      },
      {} as Record<string, ExtractionFieldConfig[]>,
    );
  }, [configs]);

  if (isLoading) {
    return (
      <div className="flex justify-center items-center p-8">
        <Loader2 className="w-8 h-8 animate-spin" />
      </div>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex justify-between items-center">
          <div>
            <CardTitle>Configure Extraction Fields</CardTitle>
            <CardDescription>
              Select the fields you want the AI to extract. Changes will apply
              to all future document uploads.
            </CardDescription>
          </div>
          <Button
            onClick={handleSaveChanges}
            disabled={isSaving || !hasChanges}
          >
            {isSaving ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Save className="mr-2 h-4 w-4" />
            )}
            Save Changes
          </Button>
        </div>
      </CardHeader>
      <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {Object.entries(groupedConfigs).map(([docType, fields]) => (
          <div key={docType} className="p-4 border rounded-lg bg-gray-50/50">
            <h3 className="font-semibold text-lg mb-4 text-black">
              {docType.replace(/([A-Z])/g, " $1").trim()}
            </h3>
            <div className="space-y-3">
              {fields.map((config) => (
                <div key={config.id} className="flex items-center space-x-3">
                  <Checkbox
                    id={String(config.id)}
                    checked={config.is_enabled}
                    onCheckedChange={() => handleToggle(config.id)}
                    disabled={config.is_essential}
                  />
                  <label
                    htmlFor={String(config.id)}
                    className={cn(
                      "text-sm font-medium leading-none",
                      config.is_essential
                        ? "text-gray-400 cursor-not-allowed"
                        : "cursor-pointer",
                    )}
                  >
                    {config.display_name}
                  </label>
                  {config.is_essential && (
                    <span className="text-xs text-gray-400">(Essential)</span>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
};
