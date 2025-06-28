
import { useState } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import JobSearch from "./JobSearch";
import AIInterview from "./AIInterview";
import { Job } from "@/types";

const Dashboard = () => {
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [activeTab, setActiveTab] = useState("search");

  const handleStartInterview = (job: Job) => {
    setSelectedJob(job);
    setActiveTab("interview");
  };

  const handleBackToSearch = () => {
    setSelectedJob(null);
    setActiveTab("search");
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-2">
          Search for jobs and practice interviews with AI
        </p>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="search">Search Jobs</TabsTrigger>
          <TabsTrigger value="interview" disabled={!selectedJob}>
            AI Interview {selectedJob && `(${selectedJob.title})`}
          </TabsTrigger>
        </TabsList>

        <TabsContent value="search" className="mt-6">
          <JobSearch onStartInterview={handleStartInterview} />
        </TabsContent>

        <TabsContent value="interview" className="mt-6">
          {selectedJob && (
            <AIInterview job={selectedJob} onBack={handleBackToSearch} />
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default Dashboard;
