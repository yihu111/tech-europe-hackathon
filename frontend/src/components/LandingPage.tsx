
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowRight, BarChart3, Briefcase, Mic } from "lucide-react";

interface LandingPageProps {
  onGetStarted: () => void;
}

const LandingPage = ({ onGetStarted }: LandingPageProps) => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center mb-16">
          <h1 className="text-5xl font-bold text-gray-900 mb-6">
            Welcome to <span className="text-blue-600">SkillScope</span>
          </h1>
          <p className="text-xl text-gray-600 max-w-3xl mx-auto mb-8">
            Visualize your GitHub skills, manage job opportunities, and practice with AI-powered interviews. 
            Take control of your career development journey.
          </p>
          <Button onClick={onGetStarted} size="lg" className="text-lg px-8 py-3">
            Get Started <ArrowRight className="ml-2 h-5 w-5" />
          </Button>
        </div>

        <div className="grid md:grid-cols-3 gap-8 mb-16">
          <Card className="text-center hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <BarChart3 className="h-6 w-6 text-blue-600" />
              </div>
              <CardTitle>Skill Graph Analysis</CardTitle>
              <CardDescription>
                Visualize your programming skills based on GitHub repository analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Enter your GitHub username and get detailed insights into your coding languages and frameworks usage.
              </p>
            </CardContent>
          </Card>

          <Card className="text-center hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <Briefcase className="h-6 w-6 text-green-600" />
              </div>
              <CardTitle>Job Management</CardTitle>
              <CardDescription>
                Save and organize job opportunities that match your skills
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Keep track of job applications and requirements in one centralized dashboard.
              </p>
            </CardContent>
          </Card>

          <Card className="text-center hover:shadow-lg transition-shadow">
            <CardHeader>
              <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
                <Mic className="h-6 w-6 text-purple-600" />
              </div>
              <CardTitle>AI Interview Practice</CardTitle>
              <CardDescription>
                Practice interviews with AI-powered voice interaction
              </CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-gray-600">
                Prepare for real interviews with realistic AI-powered mock interviews.
              </p>
            </CardContent>
          </Card>
        </div>

        <div className="bg-white rounded-lg shadow-lg p-8 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-4">Ready to level up your career?</h2>
          <p className="text-gray-600 mb-6">Join thousands of developers who are using SkillScope to advance their careers.</p>
          <Button onClick={onGetStarted} size="lg" variant="default">
            Start Your Journey
          </Button>
        </div>
      </div>
    </div>
  );
};

export default LandingPage;
