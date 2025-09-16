import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/Card";

export default function StyleGuidePage() {
  return (
    <div className="container mx-auto p-4 space-y-10">
      <section>
        <h1 className="text-3xl font-bold text-black mb-4">Style Guide</h1>
        <p className="text-gray-800 font-medium">
          This is a living style guide showcasing the core components of the
          Supervity AP Agent frontend.
        </p>
      </section>

      {/* Typography Section */}
      <section>
        <h2 className="text-2xl font-semibold text-black mb-4">Typography</h2>
        <div className="space-y-2">
          <h1 className="text-3xl font-bold text-black">
            Heading 1 (Page Title)
          </h1>
          <h2 className="text-2xl font-semibold text-black">
            Heading 2 (Section Title)
          </h2>
          <h3 className="text-xl font-semibold text-black">
            Heading 3 (Card Title)
          </h3>
          <p className="text-gray-800">
            This is a paragraph of body text. It&apos;s the default text style
            for the application, designed for readability.
          </p>
          <label className="text-gray-800 font-medium">
            This is a label for a form field.
          </label>
        </div>
      </section>

      {/* Buttons Section */}
      <section>
        <h2 className="text-2xl font-semibold text-black mb-4">Buttons</h2>
        <div className="flex flex-wrap gap-4 items-center">
          <Button variant="primary">Primary Button</Button>
          <Button variant="success">Success Button</Button>
          <Button variant="destructive">Destructive Button</Button>
          <Button variant="secondary">Secondary Button</Button>
          <Button variant="ghost">Ghost Button</Button>
          <Button variant="link">Link Button</Button>
        </div>
      </section>

      {/* Badges Section */}
      <section>
        <h2 className="text-2xl font-semibold text-black mb-4">Badges</h2>
        <div className="flex flex-wrap gap-4 items-center">
          <Badge variant="default">Default</Badge>
          <Badge variant="success">Success / Approved</Badge>
          <Badge variant="warning">Warning / Needs Review</Badge>
          <Badge variant="destructive">Destructive / Rejected</Badge>
        </div>
      </section>

      {/* Card Section */}
      <section>
        <h2 className="text-2xl font-semibold text-black mb-4">Cards</h2>
        <Card className="w-[350px]">
          <CardHeader>
            <CardTitle>Card Title</CardTitle>
            <CardDescription>
              This is a description for the card.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <p>
              This is the main content area of the card. It can hold any
              elements you need.
            </p>
          </CardContent>
        </Card>
      </section>
    </div>
  );
}
