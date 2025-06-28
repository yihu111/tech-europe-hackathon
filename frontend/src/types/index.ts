
export interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  description: string;
  jobUrl: string;
  datePosted: string;
  requirements: string[];
}

export interface SkillData {
  language: string;
  usage: number;
  color: string;
}

export interface GraphResponse {
  imageUrl: string;
  skills: SkillData[];
  totalRepos: number;
  username: string;
}

export interface User {
  id: string;
  username: string;
  email: string;
}
