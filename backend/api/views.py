from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count

from .serializers import PaperSerializer
from .models import Paper, ExtractedSkill # <-- 1. IMPORT ExtractedSkill

class PaperViewSet(viewsets.ModelViewSet):
    queryset = Paper.objects.all().order_by('title')
    serializer_class = PaperSerializer
    
    @action(detail=False, methods=['get'])
    def by_author(self, request):
        author = request.query_params.get('author', None)
        if author is not None:
            papers = Paper.objects.filter(authors__icontains=author)
            serializer = self.get_serializer(papers, many=True)
            return Response(serializer.data)
        return Response({"error": "No author specified."}, status=400)
    
    
    @action(detail=False, methods=['get'])
    def skill_profile(self, request):
        
        author = request.query_params.get('author', None)
        if not author:
            return Response({"error": "No author specified. Use ?author=..."}, status=400)

        classified_skills_query = ExtractedSkill.objects.filter(
            paper__authors__icontains=author
        )

        processed_paper_ids = classified_skills_query.values_list('paper', flat=True).distinct()
        total_papers_processed = processed_paper_ids.count()

        if total_papers_processed == 0:
            return Response({
                "error": f"No processed papers (with skills) found for author matching '{author}'."
            }, status=404)

        aggregated_skills = classified_skills_query.values(
            'skill_name',
            'level',
            'level_0_skill'
        ).annotate(
            paper_count=Count('paper', distinct=True) # นับจำนวน Paper ที่ไม่ซ้ำกัน
        ).order_by('-paper_count') # เรียงจาก Skill ที่พบบ่อยที่สุด

        response_data = {
            "author": author,
            "total_papers_processed": total_papers_processed, 
            "l0_fields": [],
            "l1_categories": [],
            "l2_specific_skills": []
        }

        for skill in aggregated_skills:
            percentage = (skill['paper_count'] / total_papers_processed) * 100
            
            skill_data = {
                "skill_name": skill['skill_name'],
                "paper_count": skill['paper_count'],
                "percentage_of_papers": round(percentage, 2)
            }
            
            if skill['level'] is not None and skill['level'] > 0 and skill['level_0_skill']:
                skill_data['l0_parent'] = skill['level_0_skill']
            
            if skill['level'] == 0:
                response_data['l0_fields'].append(skill_data)
            elif skill['level'] == 1:
                response_data['l1_categories'].append(skill_data)
            elif skill['level'] == 2:
                response_data['l2_specific_skills'].append(skill_data)

        return Response(response_data)
    
    @action(detail=False, methods=['get'])
    def paper_skills(self, request):
        """
        แสดงรายการ Skill (ExtractedSkill) ของแต่ละ Paper
        โดยค้นหาจาก Title หรือ Author
        """
        title_query = request.query_params.get('title', None)
        author_query = request.query_params.get('author', None)

        # 1. ตรวจสอบว่ามีการส่งพารามิเตอร์มาหรือไม่
        if not title_query and not author_query:
            return Response({
                "error": "Please provide 'title' or 'author' parameter to search."
            }, status=400)

        # 2. ค้นหา Paper ตามเงื่อนไข
        papers = Paper.objects.all()
        
        if title_query:
            papers = papers.filter(title__icontains=title_query)
        
        if author_query:
            papers = papers.filter(authors__icontains=author_query)

        if not papers.exists():
            return Response({"message": "No papers found matching criteria."}, status=404)

        # 3. วนลูป Paper ที่เจอเพื่อดึง Skill ของแต่ละอัน
        results = []
        for paper in papers:
            # ดึง Skill ที่เกี่ยวข้องกับ Paper นี้
            skills = ExtractedSkill.objects.filter(paper=paper).order_by('-vote_count')
            
            skills_list = []
            for skill in skills:
                skills_list.append({
                    "skill_name": skill.skill_name,
                    "level": skill.level,
                    "level_0_parent": skill.level_0_skill,
                    "vote_count": skill.vote_count
                })

            # จัดรูปแบบข้อมูลตอบกลับ
            results.append({
                "paper_id": paper.id,
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "total_skills": len(skills_list),
                "skills": skills_list
            })

        return Response(results)