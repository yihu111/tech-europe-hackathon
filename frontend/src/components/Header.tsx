
import { Button } from "@/components/ui/button";

const Header = () => {
  return (
    <header className="bg-white shadow-sm border-b">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-16">
          <div className="flex items-center">
            <h1 className="text-2xl font-bold text-blue-600">SkillScope</h1>
          </div>
          
          <div className="flex items-center space-x-4">
            <span className="text-gray-700">Welcome to SkillScope</span>
            <Button variant="outline">
              Login (Coming Soon)
            </Button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;
