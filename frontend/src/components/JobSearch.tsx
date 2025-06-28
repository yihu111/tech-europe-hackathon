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

interface OverviewResponse {
  status: string;
  username: string;
  message: string;
  result: any;
}

interface JobSearchResult {
  description: string;
  url: string;
}

const JobSearch = ({ onStartInterview }: JobSearchProps) => {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [searchingJobs, setSearchingJobs] = useState(false);
  const [overviewResult, setOverviewResult] = useState<any>(null);
  const [jobResults, setJobResults] = useState<JobSearchResult[]>([]);
  const { toast } = useToast();

  const handleGetOverview = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim()) {
      toast({
        title: "Error",
        description: "Please enter a GitHub username",
        variant: "destructive",
      });
      return;
    }

    setLoading(true);
    try {
      const response = await fetch(ENDPOINTS.OVERVIEW, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ username: username.trim() }),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: OverviewResponse = await response.json();
      setOverviewResult(data.result);
      setJobResults([]); // Clear previous job results
      
      toast({
        title: "Success",
        description: data.message || "Overview data retrieved successfully!",
      });
    } catch (error) {
      console.error("Error getting overview:", error);
      
      // For demo purposes, show mock overview data
      const mockOverview = {
        skills: ["React", "TypeScript", "Node.js", "Python"],
        experience: "Full-stack developer with 3+ years experience",
        projects: ["E-commerce platform", "Task management app", "Weather dashboard"]
      };
      setOverviewResult(mockOverview);
      
      toast({
        title: "Demo Mode",
        description: "Showing mock overview data. Connect to backend for real data.",
        variant: "default",
      });
    } finally {
      setLoading(false);
    }
  };

  const handleSearchJobs = async () => {
    if (!overviewResult) {
      toast({
        title: "Error",
        description: "Please get overview data first",
        variant: "destructive",
      });
      return;
    }

    setSearchingJobs(true);
    try {
      const response = await fetch(ENDPOINTS.JOBSEARCH, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(overviewResult),
      });
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: JobSearchResult[] = await response.json();
      setJobResults(data);
      
      toast({
        title: "Success",
        description: `Found ${data.length} job${data.length !== 1 ? 's' : ''}!`,
      });
    } catch (error) {
      console.error("Error searching jobs:", error);
      
      // For demo purposes, show mock job data
      const mockJobs: JobSearchResult[] = [
        {
          description: "Senior React Developer - Join our team building next-generation web applications with React, TypeScript, and modern web technologies. Experience with state management and testing frameworks preferred.",
          url: "https://example.com/job/react-developer",
        },
        {
          description: "Full Stack Engineer - Work with Python, FastAPI, React, and PostgreSQL in a fast-paced startup environment. Build scalable applications and collaborate with product teams.",
          url: "https://example.com/job/fullstack-engineer",
        },
      ];
      setJobResults(mockJobs);
      
      toast({
        title: "Demo Mode",
        description: "Showing mock job data. Connect to backend for real job search.",
        variant: "default",
      });
    } finally {
      setSearchingJobs(false);
    }
  };

  const handleStartInterview = (jobResult: JobSearchResult, index: number) => {
    const job: Job = {
      id: `job-${index}`,
      title: `Job Opportunity ${index + 1}`,
      company: "Various Companies",
      location: "Remote/On-site",
      description: jobResult.description,
      jobUrl: jobResult.url,
      datePosted: new Date().toISOString().split('T')[0],
      requirements: [],
    };
    
    onStartInterview(job);
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Job Search & Overview</CardTitle>
          <CardDescription>
            Get your profile overview and search for personalized job opportunities
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleGetOverview} className="flex gap-4 mb-4">
            <Input
              type="text"
              placeholder="Enter your GitHub username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Getting Overview..." : "Get Overview"}
            </Button>
          </form>
          
          {overviewResult && (
            <Button 
              onClick={handleSearchJobs} 
              disabled={searchingJobs}
              className="w-full"
            >
              {searchingJobs ? "Searching Jobs..." : "Search Jobs"}
            </Button>
          )}
        </CardContent>
      </Card>

      {overviewResult && (
        <Card>
          <CardHeader>
            <CardTitle>Profile Overview</CardTitle>
            <CardDescription>
              Your extracted profile information
            </CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="bg-gray-100 p-4 rounded whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
              {JSON.stringify(overviewResult, null, 2)}
            </pre>
          </CardContent>
        </Card>
      )}

      {jobResults.length > 0 && (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-900">Job Search Results</h2>
            <p className="text-gray-600">{jobResults.length} job{jobResults.length !== 1 ? 's' : ''} found</p>
          </div>

          <div className="grid gap-4">
            {jobResults.map((job, index) => (
              <Card key={index} className="hover:shadow-lg transition-shadow">
                <CardContent className="p-6">
                  <div className="flex justify-between items-start gap-4">
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold mb-2">Job Opportunity {index + 1}</h3>
                      <p className="text-gray-700 leading-relaxed mb-4">{job.description}</p>
                      
                      <Button variant="outline" size="sm" asChild>
                        <a href={job.url} target="_blank" rel="noopener noreferrer">
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