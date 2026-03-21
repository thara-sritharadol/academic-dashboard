from django.db.models import Count
from django.db.models.functions import Lower
from api.models import Author, Paper

class DataDeduplicationService:
    
    @staticmethod
    def merge_duplicate_authors():
        total_merged = 0
        total_deleted = 0

        # ==========================================
        # PASS 1: Merge by OpenAlex ID
        # ==========================================
        duplicates_by_id = (
            Author.objects.exclude(openalex_id__isnull=True).exclude(openalex_id__exact="")
            .values('openalex_id')
            .annotate(id_count=Count('id'))
            .filter(id_count__gt=1)
        )

        for dup in duplicates_by_id:
            oa_id = dup['openalex_id']
            matching_authors = list(Author.objects.filter(openalex_id=oa_id))
            
            if len(matching_authors) < 2:
                continue
            
            # 🔥 THE FIX: จัดเรียงด้วย Python ให้คนที่มี Faculty ขึ้นก่อนเสมอ
            matching_authors.sort(
                key=lambda a: (
                    bool(a.faculty and a.faculty.strip()), # ความสำคัญที่ 1: ต้องมีชื่อคณะ
                    len(a.name)                            # ความสำคัญที่ 2: ถ้ามีคณะทั้งคู่ เอาคนชื่อยาวกว่า
                ),
                reverse=True
            )
                
            primary_author = matching_authors[0]
            duplicates_to_merge = matching_authors[1:]
            
            for duplicate in duplicates_to_merge:
                # 1. โอนย้าย Papers
                for paper in duplicate.papers.all():
                    paper.authors.add(primary_author)
                    paper.authors.remove(duplicate)
                
                # 2. เก็บข้อมูลสำคัญเผื่อร่างต้นไม่มี
                should_update_name = len(duplicate.name) > len(primary_author.name) and not primary_author.faculty
                new_name = duplicate.name
                email_to_transfer = duplicate.email
                inst_to_transfer = duplicate.institution
                
                # 3. ลบร่างโคลน
                duplicate.delete()
                total_deleted += 1
                
                # 4. ถมข้อมูลให้ร่างต้น
                needs_save = False
                if should_update_name:
                     primary_author.name = new_name
                     needs_save = True
                if email_to_transfer and not primary_author.email:
                     primary_author.email = email_to_transfer
                     needs_save = True
                if inst_to_transfer and not primary_author.institution:
                     primary_author.institution = inst_to_transfer
                     needs_save = True
                     
                if needs_save:
                     primary_author.save()
                     
            total_merged += 1

        # ==========================================
        # PASS 2: Merge by Name (เผื่อเก็บตกคนที่ไม่มี ID)
        # ==========================================
        duplicates_by_name = (
            Author.objects.annotate(name_lower=Lower('name'))
            .values('name_lower')
            .annotate(name_count=Count('id'))
            .filter(name_count__gt=1)
        )

        for dup in duplicates_by_name:
            name_lower = dup['name_lower']
            matching_authors = list(Author.objects.filter(name__iexact=name_lower))
            
            if len(matching_authors) < 2:
                continue
            
            # 🔥 THE FIX: จัดเรียงด้วย Python ให้คนที่มี Faculty ขึ้นก่อน
            matching_authors.sort(
                key=lambda a: (
                    bool(a.faculty and a.faculty.strip()), # ความสำคัญที่ 1: ต้องมีชื่อคณะ
                    bool(a.openalex_id)                    # ความสำคัญที่ 2: ต้องมี OpenAlex ID
                ),
                reverse=True
            )
                
            primary_author = matching_authors[0]
            duplicates_to_merge = matching_authors[1:]
            
            for duplicate in duplicates_to_merge:
                # 1. โอนย้าย Papers
                for paper in duplicate.papers.all():
                    paper.authors.add(primary_author)
                    paper.authors.remove(duplicate)
                
                # 2. ดึงข้อมูลออกมาเก็บไว้ชั่วคราว
                oa_id_to_transfer = duplicate.openalex_id
                email_to_transfer = duplicate.email
                inst_to_transfer = duplicate.institution
                
                # 3. ลบร่างโคลนเพื่อปลดล็อค DB Constraint
                duplicate.delete()
                total_deleted += 1
                
                # 4. อัปเดตร่างต้น
                needs_save = False
                if oa_id_to_transfer and not primary_author.openalex_id:
                    primary_author.openalex_id = oa_id_to_transfer
                    needs_save = True
                if email_to_transfer and not primary_author.email:
                    primary_author.email = email_to_transfer
                    needs_save = True
                if inst_to_transfer and not primary_author.institution:
                    primary_author.institution = inst_to_transfer
                    needs_save = True
                    
                if needs_save:
                    primary_author.save()
                    
            total_merged += 1

        return {
            "status": "success", 
            "merged": total_merged, 
            "deleted": total_deleted,
            "message": f"Merged {total_merged} unique profiles. Deleted {total_deleted} duplicates."
        }

    @staticmethod
    def merge_duplicate_papers():
        duplicates = (
            Paper.objects.annotate(title_lower=Lower('title'))
            .values('title_lower')
            .annotate(paper_count=Count('id'))
            .filter(paper_count__gt=1)
        )

        if not duplicates:
            return {"status": "success", "merged": 0, "deleted": 0, "message": "No duplicate papers found."}

        total_merged = 0
        total_deleted = 0

        for dup in duplicates:
            title_lower = dup['title_lower']
            matching_papers = list(Paper.objects.filter(title__iexact=title_lower).order_by('-citation_count'))
            
            if len(matching_papers) < 2:
                continue

            primary_paper = matching_papers[0]
            duplicates_to_merge = matching_papers[1:]

            for duplicate in duplicates_to_merge:
                for author in duplicate.authors.all():
                    primary_paper.authors.add(author)
                
                if duplicate.abstract and not primary_paper.abstract:
                    primary_paper.abstract = duplicate.abstract
                
                if duplicate.cluster_id and not primary_paper.cluster_id:
                    primary_paper.cluster_id = duplicate.cluster_id
                    primary_paper.cluster_label = duplicate.cluster_label
                    primary_paper.predicted_multi_labels = duplicate.predicted_multi_labels
                    primary_paper.topic_keywords = duplicate.topic_keywords
                    primary_paper.topic_distribution = duplicate.topic_distribution

                primary_paper.save()
                duplicate.delete()
                total_deleted += 1
            
            total_merged += 1

        return {
            "status": "success", 
            "merged": total_merged, 
            "deleted": total_deleted,
            "message": f"Processed {total_merged} duplicate groups. Removed {total_deleted} redundant papers."
        }