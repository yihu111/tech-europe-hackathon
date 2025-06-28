
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";
import { Job } from "@/types";
import { useToast } from "@/hooks/use-toast";
import { ENDPOINTS } from "@/config/env";

interface JobSearchProps {
  onStartInterview: (job: Job) => void;
}

interface SearchJob {
  job_description: string;
  job_url: string;
}

const JobSearch = ({ onStartInterview }: JobSearchProps) => {
  const [searchQuery, setSearchQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<SearchJob[]>([]);
  const { toast } = useToast();

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) {
      toast({
        title: "Error",
        description: "Please enter a search query",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(ENDPOINTS.SEARCH, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username: searchQuery }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: SearchJob[] = await response.json();
      setJobs(data);
      
      toast({
        title: "Success",
        description: `Found ${data.length} job${data.length !== 1 ? 's' : ''}!`,
      });
    } catch (error) {
      console.error("Error searching jobs:", error);
      
      // For demo purposes, show mock data
      const mockJobs: SearchJob[] = [
        {
          job_description: "We are looking for a Senior React Developer to join our team. You will be responsible for building user interfaces using React, TypeScript, and modern web technologies. Experience with state management libraries like Redux or Zustand is preferred.",
          job_url: "https://example.com/job/react-developer",
        },
        {
          job_description: "Full Stack Engineer position available for a fast-growing startup. Work with Python, FastAPI, React, and PostgreSQL. You'll be building scalable web applications and working closely with our product team.",
          job_url: "https://example.com/job/fullstack-engineer",
        },
        {
          job_description: "DevOps Engineer role focusing on AWS infrastructure. Experience with Docker, Kubernetes, and CI/CD pipelines required. You'll help scale our cloud infrastructure and improve deployment processes.",
          job_url: "https://example.com/job/devops-engineer",
        },
      ];
      setJobs(mockJobs);
      
      toast({
        title: "Demo Mode",
        description: "Showing mock job data. Connect to backend for real job search.",
        variant: "default",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = (searchJob: SearchJob, index: number) => {
    // Convert SearchJob to Job format for the interview
    const job: Job = {
      id: `search-${index}`,
      title: `Job ${index + 1}`,
      company: "Various Companies",
      location: "Remote/On-site",
      description: searchJob.job_description,
      jobUrl: searchJob.job_url,
      datePosted: new Date().toISOString().split('T')[0],
      requirements: [], // Will be extracted from description in interview
    };
    
    onStartInterview(job);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Job Search</CardTitle>
          <CardDescription>
            Search for job opportunities and practice interviews with AI
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSearch} className="flex gap-4">
            <Input
              type="text"
              placeholder="Enter your GitHub username"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Searching..." : "Search Jobs"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {jobs.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900">Search Results</h2>
            <p className="text-gray-600">{jobs.length} job{jobs.length !== 1 ? 's' : ''} found</p>
          </div>

          <div className="grid gap-4">
            {jobs.map((job, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold mb-2">Job Opportunity {index + 1}</h3>
                      <p className="text-gray-700 leading-relaxed mb-4">{job.job_description}</p>
                      
                      <Button variant="outline" size="sm" asChild>
                        <a href={job.job_url} target="_blank" rel="noopener noreferrer">
                          <ExternalLink className="w-4 h-4 mr-2" />
                          View Job
                        </a>
                      </Button>
                    </div>
                    
                    <div className="flex-shrink-0">
                      <Button onClick={() => handleStartInterview(job, index)}>
                        Mock Interview
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default JobSearch;
