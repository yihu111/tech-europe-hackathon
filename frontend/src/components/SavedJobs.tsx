
import { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { ExternalLink, Mic } from "lucide-react";
import { Job } from "@/types";
import { useToast } from "@/hooks/use-toast";

interface SavedJobsProps {
  onStartInterview: (job: Job) => void;
}

const SavedJobs = ({ onStartInterview }: SavedJobsProps) => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      // Replace with your FastAPI backend URL
      const response = await fetch("http://127.0.0.1:8000/jobs");
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: Job[] = await response.json();
      setJobs(data);
    } catch (error) {
      console.error("Error fetching jobs:", error);
      
      // For demo purposes, show mock data
      const mockJobs: Job[] = [
        {
          id: "1",
          title: "Senior Frontend Developer",
          company: "TechCorp Inc.",
          location: "San Francisco, CA",
          description: "We're looking for a senior frontend developer with expertise in React, TypeScript, and modern web technologies. You'll be working on cutting-edge applications used by millions of users.",
          jobUrl: "https://example.com/job/1",
          datePosted: "2024-01-15",
          requirements: ["React", "TypeScript", "CSS", "Node.js"],
        },
        {
          id: "2",
          title: "Full Stack Engineer",
          company: "StartupXYZ",
          location: "Remote",
          description: "Join our fast-growing startup as a full stack engineer. Work with Python, FastAPI, React, and PostgreSQL to build innovative solutions.",
          jobUrl: "https://example.com/job/2",
          datePosted: "2024-01-12",
          requirements: ["Python", "FastAPI", "React", "PostgreSQL"],
        },
        {
          id: "3",
          title: "DevOps Engineer",
          company: "CloudTech Solutions",
          location: "Austin, TX",
          description: "Looking for a DevOps engineer to help scale our infrastructure. Experience with AWS, Docker, and Kubernetes required.",
          jobUrl: "https://example.com/job/3",
          datePosted: "2024-01-10",
          requirements: ["AWS", "Docker", "Kubernetes", "Python"],
        },
      ];
      setJobs(mockJobs);
      
      toast({
        title: "Demo Mode",
        description: "Showing mock job data. Connect to FastAPI backend for real job listings.",
      });
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-600">Loading saved jobs...</div>
      </div>
    );
  }

  if (jobs.length === 0) {
    return (
      <Card>
        <CardContent className="text-center py-12">
          <h3 className="text-lg font-semibold text-gray-900 mb-2">No saved jobs yet</h3>
          <p className="text-gray-600">Start saving job opportunities to see them here.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Saved Jobs</h2>
        <p className="text-gray-600">{jobs.length} job{jobs.length !== 1 ? 's' : ''} saved</p>
      </div>

      <div className="grid gap-6">
        {jobs.map((job) => (
          <Card key={job.id} className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="flex justify-between items-start">
                <div className="flex-1">
                  <CardTitle className="text-xl">{job.title}</CardTitle>
                  <CardDescription className="text-lg font-medium text-gray-700 mt-1">
                    {job.company} • {job.location}
                  </CardDescription>
                </div>
                <div className="text-sm text-gray-500">
                  Posted: {new Date(job.datePosted).toLocaleDateString()}
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-700 leading-relaxed">{job.description}</p>
              
              <div className="flex flex-wrap gap-2">
                {job.requirements.map((req) => (
                  <Badge key={req} variant="secondary">
                    {req}
                  </Badge>
                ))}
              </div>
              
              <div className="flex gap-3 pt-4">
                <Button variant="outline" asChild>
                  <a href={job.jobUrl} target="_blank" rel="noopener noreferrer">
                    <ExternalLink className="w-4 h-4 mr-2" />
                    View Job
                  </a>
                </Button>
                <Button onClick={() => onStartInterview(job)}>
                  <Mic className="w-4 h-4 mr-2" />
                  Start AI Interview
                </Button>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
};

export default SavedJobs;
