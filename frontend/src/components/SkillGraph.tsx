
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { GraphResponse } from "@/types";
import { useToast } from "@/hooks/use-toast";

const SkillGraph = () => {
  const [username, setUsername] = useState("");
  const [loading, setLoading] = useState(false);
  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const { toast } = useToast();

  const handleSubmit = async (e: React.FormEvent) => {
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
      // Replace with your FastAPI backend URL
      const response = await fetch(`http://127.0.0.1:8000/graph?username=${encodeURIComponent(username)}`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: GraphResponse = await response.json();
      setGraphData(data);
      
      toast({
        title: "Success",
        description: "Skill graph generated successfully!",
      });
    } catch (error) {
      console.error("Error fetching skill graph:", error);
      
      // For demo purposes, show mock data
      const mockData: GraphResponse = {
        imageUrl: "/placeholder.svg",
        skills: [
          { language: "JavaScript", usage: 45, color: "#f1e05a" },
          { language: "TypeScript", usage: 30, color: "#2b7489" },
          { language: "Python", usage: 15, color: "#3572A5" },
          { language: "CSS", usage: 10, color: "#563d7c" },
        ],
        totalRepos: 25,
        username: username,
      };
      setGraphData(mockData);
      
      toast({
        title: "Demo Mode",
        description: "Showing mock data. Connect to FastAPI backend for real analysis.",
        variant: "default",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>GitHub Skill Analysis</CardTitle>
          <CardDescription>
            Enter your GitHub username to analyze your programming skills and generate a visual graph
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="flex gap-4">
            <Input
              type="text"
              placeholder="Enter GitHub username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="flex-1"
            />
            <Button type="submit" disabled={loading}>
              {loading ? "Analyzing..." : "Generate Graph"}
            </Button>
          </form>
        </CardContent>
      </Card>

      {graphData && (
        <div className="grid lg:grid-cols-2 gap-6">
          <Card>
            <CardHeader>
              <CardTitle>Skill Graph for {graphData.username}</CardTitle>
              <CardDescription>
                Based on analysis of {graphData.totalRepos} repositories
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="aspect-square bg-gray-100 rounded-lg flex items-center justify-center">
                <img 
                  src={graphData.imageUrl} 
                  alt="Skill Graph" 
                  className="max-w-full max-h-full object-contain"
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.src = "/placeholder.svg";
                  }}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Skills Breakdown</CardTitle>
              <CardDescription>
                Detailed analysis of your programming languages
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Language</TableHead>
                    <TableHead>Usage %</TableHead>
                    <TableHead>Visual</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {graphData.skills.map((skill) => (
                    <TableRow key={skill.language}>
                      <TableCell className="font-medium">{skill.language}</TableCell>
                      <TableCell>{skill.usage}%</TableCell>
                      <TableCell>
                        <div className="w-full bg-gray-200 rounded-full h-2">
                          <div
                            className="h-2 rounded-full"
                            style={{
                              width: `${skill.usage}%`,
                              backgroundColor: skill.color,
                            }}
                          />
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default SkillGraph;
