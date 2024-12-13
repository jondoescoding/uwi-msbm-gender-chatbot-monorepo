import { Card } from "@/components/ui/card";
import { ExternalLink } from "lucide-react";

interface ArticleCardProps {
  title: string;
  link: string;
  media_source: string;
  published_date: string;
  msbm_country_full_name: string;
  msbm_category: string;
  msbm_llm_summary: string;
}

const ArticleCard = ({
  title,
  link,
  media_source,
  published_date,
  msbm_country_full_name,
  msbm_category,
  msbm_llm_summary
}: ArticleCardProps): JSX.Element => {
  return (
    <Card className="p-6 bg-black/40 backdrop-blur-xl border border-white/10 transition-all duration-300 hover:border-white/30 hover:bg-white/5">
      <div className="space-y-4">
        {/* Title and Link */}
        <div className="flex items-start justify-between gap-4">
          <h3 className="text-lg font-medium text-white flex-1">{title}</h3>
          <a
            href={link}
            target="_blank"
            rel="noopener noreferrer"
            className="text-blue-400 hover:text-blue-300 transition-colors"
          >
            <ExternalLink className="h-5 w-5" />
          </a>
        </div>

        {/* Metadata */}
        <div className="grid grid-cols-2 gap-4 text-sm text-gray-400">
          <div>
            <span className="font-medium text-gray-500">Source:</span>{" "}
            <a 
              href={link} 
              target="_blank" 
              rel="noopener noreferrer"
              className="hover:text-blue-400 transition-colors"
            >
              {media_source}
            </a>
          </div>
          <div>
            <span className="font-medium text-gray-500">Date:</span>{" "}
            {published_date}
          </div>
          <div>
            <span className="font-medium text-gray-500">Country:</span>{" "}
            {msbm_country_full_name}
          </div>
          <div>
            <span className="font-medium text-gray-500">Category:</span>{" "}
            <span className="capitalize">{msbm_category}</span>
          </div>
        </div>

        {/* Summary */}
        <div className="text-sm text-gray-300">
          <div className="font-medium text-gray-500 mb-2">Summary:</div>
          <p className="line-clamp-4 leading-relaxed">
            {msbm_llm_summary || "No summary available"}
          </p>
        </div>
      </div>
    </Card>
  );
};

export default ArticleCard;